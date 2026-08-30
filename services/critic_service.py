from __future__ import annotations

import inspect
import json
import re
import uuid

from dataclasses import (
    asdict,
    is_dataclass,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from threading import RLock
from typing import (
    Any,
    get_args,
    get_origin,
)

from agents.critic import (
    CriticReport,
    critic_report_from_dict,
)
from core.exceptions import CriticError


JSON_FENCE_PATTERN = re.compile(
    r"^```(?:json)?\s*|\s*```$",
    flags=re.IGNORECASE,
)


INTERNAL_OUTPUT_MARKERS = (
    "STEP COMPLETE",
    "PLAN GOAL UPDATE",
    "CURRENT STEP COMPLETE",
    "REASONING FINDINGS",
    "NEXT STEP",
)


CRITIC_JSON_KEYS = {
    "critic_summary",
    "critic_findings",
    "original_answer",
    "original_output",
    "user_request",
    "requires_revision",
    "quality_score",
}


class CriticService:
    """
    Review and optionally revise local Ollama responses.

    The critic's structured JSON is kept internal. Only the original
    answer or a validated natural-language revision is returned to
    the user-facing workflow.
    """

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.settings = self._resolve_dependency(
            args,
            kwargs,
            explicit_names=(
                "settings",
                "app_settings",
                "config",
            ),
            required_attributes=(
                "ollama_chat_model",
            ),
        )

        self.ai = self._resolve_dependency(
            args,
            kwargs,
            explicit_names=(
                "ollama",
                "ollama_service",
                "model_service",
                "llm",
            ),
            required_attributes=(
                "chat",
            ),
        )

        self.report_folder = (
            self._resolve_report_folder(
                args,
                kwargs,
            )
        )

        self.report_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = RLock()

    @staticmethod
    def _resolve_dependency(
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        explicit_names: tuple[str, ...],
        required_attributes: tuple[str, ...],
    ) -> Any | None:
        for name in explicit_names:
            value = kwargs.get(
                name
            )

            if value is not None:
                return value

        for value in args:
            if value is None:
                continue

            if all(
                hasattr(
                    value,
                    attribute,
                )
                for attribute
                in required_attributes
            ):
                return value

        return None

    def _resolve_report_folder(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Path:
        explicit_names = (
            "report_folder",
            "critic_folder",
            "review_folder",
            "storage_folder",
            "folder",
        )

        for name in explicit_names:
            value = kwargs.get(
                name
            )

            if value:
                return Path(
                    value
                ).expanduser()

        for value in args:
            if isinstance(
                value,
                Path,
            ):
                return value.expanduser()

            if isinstance(
                value,
                str,
            ):
                candidate = value.strip()

                if candidate:
                    return Path(
                        candidate
                    ).expanduser()

        if self.settings is not None:
            setting_names = (
                "critic_folder",
                "critic_report_folder",
                "review_folder",
                "reviews_folder",
                "report_folder",
            )

            for name in setting_names:
                value = getattr(
                    self.settings,
                    name,
                    None,
                )

                if value:
                    return Path(
                        value
                    ).expanduser()

            data_folder = getattr(
                self.settings,
                "data_folder",
                None,
            )

            if data_folder:
                return (
                    Path(
                        data_folder
                    ).expanduser()
                    / "critic"
                )

        return (
            Path.cwd()
            / "data"
            / "critic"
        )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        )

    @staticmethod
    def _extract_response_text(
        response: Any,
    ) -> str:
        if response is None:
            return ""

        if isinstance(
            response,
            str,
        ):
            return response.strip()

        if isinstance(
            response,
            dict,
        ):
            direct_candidates = (
                response.get(
                    "content"
                ),
                response.get(
                    "response"
                ),
                response.get(
                    "text"
                ),
            )

            for candidate in direct_candidates:
                if isinstance(
                    candidate,
                    str,
                ) and candidate.strip():
                    return candidate.strip()

            message = response.get(
                "message"
            )

            if isinstance(
                message,
                dict,
            ):
                content = message.get(
                    "content"
                )

                if isinstance(
                    content,
                    str,
                ):
                    return content.strip()

        message = getattr(
            response,
            "message",
            None,
        )

        if message is not None:
            content = getattr(
                message,
                "content",
                None,
            )

            if isinstance(
                content,
                str,
            ):
                return content.strip()

            if isinstance(
                message,
                dict,
            ):
                content = message.get(
                    "content"
                )

                if isinstance(
                    content,
                    str,
                ):
                    return content.strip()

        for attribute in (
            "content",
            "response",
            "text",
        ):
            value = getattr(
                response,
                attribute,
                None,
            )

            if isinstance(
                value,
                str,
            ) and value.strip():
                return value.strip()

        return str(
            response
        ).strip()

    def _call_model(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        system_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        if self.ai is None:
            raise CriticError(
                "The critic service has no Ollama service."
            )

        chat_method = getattr(
            self.ai,
            "chat",
            None,
        )

        if not callable(
            chat_method
        ):
            raise CriticError(
                "The configured Ollama service does not "
                "provide a chat method."
            )

        try:
            response = chat_method(
                messages=messages,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
            )

        except TypeError:
            try:
                response = chat_method(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        *messages,
                    ],
                    options={
                        "temperature": temperature,
                    },
                )

            except Exception as exc:
                raise CriticError(
                    f"Critic model request failed: {exc}"
                ) from exc

        except Exception as exc:
            raise CriticError(
                f"Critic model request failed: {exc}"
            ) from exc

        return self._extract_response_text(
            response
        )

    @staticmethod
    def _strip_code_fences(
        value: str,
    ) -> str:
        cleaned = str(
            value or ""
        ).strip()

        cleaned = JSON_FENCE_PATTERN.sub(
            "",
            cleaned,
        )

        return cleaned.strip()

    @classmethod
    def _parse_json_object(
        cls,
        value: str,
    ) -> dict[str, Any]:
        cleaned = cls._strip_code_fences(
            value
        )

        if not cleaned:
            raise ValueError(
                "The critic returned an empty response."
            )

        try:
            parsed = json.loads(
                cleaned
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()

        for index, character in enumerate(
            cleaned
        ):
            if character != "{":
                continue

            try:
                parsed, _ = decoder.raw_decode(
                    cleaned[index:]
                )

            except json.JSONDecodeError:
                continue

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        raise ValueError(
            "The critic response did not contain "
            "a valid JSON object."
        )

    @staticmethod
    def _normalise_score(
        value: Any,
        *,
        default: float,
    ) -> float:
        try:
            score = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return default

        if score > 1.0 and score <= 100.0:
            score /= 100.0

        return max(
            0.0,
            min(
                1.0,
                score,
            ),
        )

    @staticmethod
    def _normalise_severity(
        value: Any,
    ) -> str:
        cleaned = str(
            value or "warning"
        ).strip().lower()

        aliases = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "info",
            "notice": "info",
        }

        cleaned = aliases.get(
            cleaned,
            cleaned,
        )

        if cleaned not in {
            "error",
            "warning",
            "info",
        }:
            return "warning"

        return cleaned

    @classmethod
    def _normalise_findings(
        cls,
        value: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(
            value,
            list,
        ):
            return []

        findings: list[
            dict[str, Any]
        ] = []

        for item in value:
            if isinstance(
                item,
                str,
            ):
                message = item.strip()

                if not message:
                    continue

                findings.append(
                    {
                        "category": "other",
                        "severity": "warning",
                        "message": message,
                        "recommendation": "",
                        "evidence": "",
                    }
                )

                continue

            if not isinstance(
                item,
                dict,
            ):
                continue

            message = str(
                item.get(
                    "message"
                )
                or item.get(
                    "finding"
                )
                or item.get(
                    "issue"
                )
                or ""
            ).strip()

            if not message:
                continue

            findings.append(
                {
                    "category": str(
                        item.get(
                            "category",
                            "other",
                        )
                    ).strip()
                    or "other",
                    "severity": (
                        cls._normalise_severity(
                            item.get(
                                "severity",
                                "warning",
                            )
                        )
                    ),
                    "message": message,
                    "recommendation": str(
                        item.get(
                            "recommendation"
                        )
                        or item.get(
                            "fix"
                        )
                        or ""
                    ).strip(),
                    "evidence": str(
                        item.get(
                            "evidence",
                            "",
                        )
                    ).strip(),
                }
            )

        return findings

    @classmethod
    def _normalise_review_payload(
        cls,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        summary = str(
            value.get(
                "summary"
            )
            or value.get(
                "critic_summary"
            )
            or value.get(
                "review"
            )
            or "The answer was reviewed."
        ).strip()

        findings = cls._normalise_findings(
            value.get(
                "findings"
            )
            or value.get(
                "critic_findings"
            )
            or value.get(
                "issues"
            )
            or []
        )

        score = cls._normalise_score(
            value.get(
                "score"
            )
            if value.get(
                "score"
            ) is not None
            else value.get(
                "quality_score"
            ),
            default=0.75,
        )

        explicit_revision = value.get(
            "requires_revision"
        )

        if isinstance(
            explicit_revision,
            bool,
        ):
            requires_revision = (
                explicit_revision
            )

        else:
            requires_revision = (
                score < 0.8
                or any(
                    finding.get(
                        "severity"
                    )
                    == "error"
                    for finding in findings
                )
            )

        return {
            "summary": summary,
            "score": score,
            "requires_revision": (
                requires_revision
            ),
            "findings": findings,
        }

    @staticmethod
    def _serialise_value(
        value: Any,
    ) -> Any:
        if value is None:
            return None

        if isinstance(
            value,
            dict,
        ):
            return {
                str(
                    key
                ): CriticService._serialise_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                CriticService._serialise_value(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            datetime,
        ):
            return value.isoformat()

        to_dict = getattr(
            value,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):
            return CriticService._serialise_value(
                to_dict()
            )

        model_dump = getattr(
            value,
            "model_dump",
            None,
        )

        if callable(
            model_dump
        ):
            return CriticService._serialise_value(
                model_dump()
            )

        if is_dataclass(
            value
        ):
            return CriticService._serialise_value(
                asdict(
                    value
                )
            )

        return str(
            value
        )

    @staticmethod
    def _report_to_dict(
        report: CriticReport,
    ) -> dict[str, Any]:
        to_dict = getattr(
            report,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):
            result = to_dict()

            if isinstance(
                result,
                dict,
            ):
                return result

        model_dump = getattr(
            report,
            "model_dump",
            None,
        )

        if callable(
            model_dump
        ):
            result = model_dump()

            if isinstance(
                result,
                dict,
            ):
                return result

        if is_dataclass(
            report
        ):
            return asdict(
                report
            )

        result: dict[str, Any] = {}

        for name in dir(
            report
        ):
            if name.startswith(
                "_"
            ):
                continue

            try:
                value = getattr(
                    report,
                    name,
                )

            except Exception:
                continue

            if callable(
                value
            ):
                continue

            result[name] = value

        return result

    @staticmethod
    def _get_report_value(
        report: CriticReport,
        names: tuple[str, ...],
        default: Any = None,
    ) -> Any:
        for name in names:
            value = getattr(
                report,
                name,
                None,
            )

            if value is not None:
                return value

        report_data = (
            CriticService._report_to_dict(
                report
            )
        )

        for name in names:
            if (
                name in report_data
                and report_data[name] is not None
            ):
                return report_data[
                    name
                ]

        return default

    @staticmethod
    def _default_for_annotation(
        annotation: Any,
        *,
        field_name: str,
        payload: dict[str, Any],
    ) -> Any:
        origin = get_origin(
            annotation
        )

        arguments = get_args(
            annotation
        )

        if origin is not None:
            if origin in {
                list,
                tuple,
                set,
            }:
                return []

            if origin is dict:
                return {}

            if type(
                None
            ) in arguments:
                return None

        if annotation is str:
            string_defaults = {
                "id": payload.get(
                    "id",
                    str(
                        uuid.uuid4()
                    ),
                ),
                "user_request": payload.get(
                    "user_request",
                    "",
                ),
                "original_output": payload.get(
                    "original_output",
                    "",
                ),
                "original_answer": payload.get(
                    "original_answer",
                    "",
                ),
                "summary": payload.get(
                    "summary",
                    "",
                ),
                "critic_summary": payload.get(
                    "critic_summary",
                    "",
                ),
                "revised_output": payload.get(
                    "revised_output",
                    "",
                ),
                "revised_answer": payload.get(
                    "revised_answer",
                    "",
                ),
            }

            return str(
                string_defaults.get(
                    field_name,
                    "",
                )
            )

        if annotation is bool:
            return bool(
                payload.get(
                    field_name,
                    False,
                )
            )

        if annotation is float:
            return float(
                payload.get(
                    field_name,
                    0.0,
                )
            )

        if annotation is int:
            return int(
                payload.get(
                    field_name,
                    0,
                )
            )

        if annotation is datetime:
            return CriticService._utc_now()

        return None

    @classmethod
    def _construct_report(
        cls,
        payload: dict[str, Any],
    ) -> CriticReport:
        try:
            return critic_report_from_dict(
                payload
            )

        except Exception as first_error:
            model_fields = getattr(
                CriticReport,
                "model_fields",
                None,
            )

            if isinstance(
                model_fields,
                dict,
            ):
                filtered: dict[
                    str,
                    Any
                ] = {}

                for name, field in (
                    model_fields.items()
                ):
                    if name in payload:
                        filtered[name] = payload[
                            name
                        ]
                        continue

                    default = getattr(
                        field,
                        "default",
                        None,
                    )

                    default_factory = getattr(
                        field,
                        "default_factory",
                        None,
                    )

                    if callable(
                        default_factory
                    ):
                        filtered[name] = (
                            default_factory()
                        )
                        continue

                    if (
                        default is not None
                        and default.__class__.__name__
                        not in {
                            "PydanticUndefinedType",
                        }
                    ):
                        filtered[name] = default
                        continue

                    annotation = getattr(
                        field,
                        "annotation",
                        Any,
                    )

                    filtered[name] = (
                        cls._default_for_annotation(
                            annotation,
                            field_name=name,
                            payload=payload,
                        )
                    )

                try:
                    return CriticReport(
                        **filtered
                    )

                except Exception:
                    pass

            try:
                signature = inspect.signature(
                    CriticReport
                )

                constructor_values: dict[
                    str,
                    Any
                ] = {}

                for name, parameter in (
                    signature.parameters.items()
                ):
                    if name in {
                        "self",
                        "args",
                        "kwargs",
                    }:
                        continue

                    if name in payload:
                        constructor_values[name] = (
                            payload[name]
                        )
                        continue

                    if (
                        parameter.default
                        is not inspect.Parameter.empty
                    ):
                        continue

                    constructor_values[name] = (
                        cls._default_for_annotation(
                            parameter.annotation,
                            field_name=name,
                            payload=payload,
                        )
                    )

                return CriticReport(
                    **constructor_values
                )

            except Exception as exc:
                raise CriticError(
                    "Could not construct a critic report: "
                    f"{first_error}; {exc}"
                ) from exc

    def _create_report(
        self,
        *,
        user_request: str,
        original_output: str,
        review: dict[str, Any],
        route: Any,
        plan: Any,
        execution: Any,
        document_sources: list[dict[str, Any]],
        tool_result: Any,
        skill: Any,
        metadata: dict[str, Any] | None = None,
    ) -> CriticReport:
        report_id = str(
            uuid.uuid4()
        )

        created_at = (
            self._utc_now()
            .isoformat()
        )

        summary = str(
            review.get(
                "summary",
                "The answer was reviewed.",
            )
        )

        score = self._normalise_score(
            review.get(
                "score"
            ),
            default=1.0,
        )

        requires_revision = bool(
            review.get(
                "requires_revision",
                False,
            )
        )

        findings = self._normalise_findings(
            review.get(
                "findings",
                [],
            )
        )

        payload = {
            "id": report_id,
            "created_at": created_at,
            "updated_at": created_at,
            "user_request": user_request,
            "original_output": original_output,
            "original_answer": original_output,
            "output": original_output,
            "summary": summary,
            "critic_summary": summary,
            "score": score,
            "quality_score": score,
            "requires_revision": requires_revision,
            "findings": findings,
            "critic_findings": findings,
            "route": self._serialise_value(
                route
            ),
            "plan": self._serialise_value(
                plan
            ),
            "execution": self._serialise_value(
                execution
            ),
            "document_sources": (
                self._serialise_value(
                    document_sources
                )
            ),
            "tool_result": self._serialise_value(
                tool_result
            ),
            "skill": self._serialise_value(
                skill
            ),
            "revised_output": None,
            "revised_answer": None,
            "revision_applied": False,
            "metadata": metadata or {},
        }

        return self._construct_report(
            payload
        )

    def _create_safe_fallback_report(
        self,
        *,
        user_request: str,
        original_output: str,
        route: Any,
        plan: Any,
        execution: Any,
        document_sources: list[dict[str, Any]],
        tool_result: Any,
        skill: Any,
        reason: str,
    ) -> CriticReport:
        return self._create_report(
            user_request=user_request,
            original_output=original_output,
            review={
                "summary": (
                    "The critic response could not be "
                    "validated. The original answer was preserved."
                ),
                "score": 1.0,
                "requires_revision": False,
                "findings": [],
            },
            route=route,
            plan=plan,
            execution=execution,
            document_sources=document_sources,
            tool_result=tool_result,
            skill=skill,
            metadata={
                "critic_fallback": True,
                "fallback_reason": reason,
            },
        )

    def review_output(
        self,
        *,
        user_request: str,
        output: str,
        model: str,
        route: Any = None,
        plan: Any = None,
        execution: Any = None,
        document_sources: list[
            dict[str, Any]
        ] | None = None,
        tool_result: Any = None,
        skill: Any = None,
        **_: Any,
    ) -> CriticReport:
        cleaned_request = str(
            user_request or ""
        ).strip()

        cleaned_output = str(
            output or ""
        ).strip()

        if not cleaned_output:
            raise CriticError(
                "The critic cannot review an empty answer."
            )

        sources = [
            source
            for source in (
                document_sources
                or []
            )
            if isinstance(
                source,
                dict,
            )
        ]

        system_prompt = """
You are the internal quality critic for TechCorp AI.

Review the proposed answer against the user's request and the
supplied evidence.

Return exactly one JSON object with this structure:

{
  "summary": "Brief assessment",
  "score": 0.0,
  "requires_revision": false,
  "findings": [
    {
      "category": "accuracy",
      "severity": "error",
      "message": "Specific problem",
      "recommendation": "Specific correction",
      "evidence": "Relevant source label or explanation"
    }
  ]
}

Rules:

- score must be a number from 0.0 to 1.0.
- severity must be error, warning or info.
- Do not repeat the full original answer.
- Do not provide a revised answer.
- Do not include Markdown code fences.
- Do not invent sources or URLs.
- Judge web claims only against supplied web evidence.
- Judge document claims only against supplied document evidence.
- A missing source is not automatically an error when the user did
  not request research or evidence.
- Do not expose private chain-of-thought.
""".strip()

        review_payload = {
            "user_request": cleaned_request,
            "proposed_answer": cleaned_output,
            "route": self._serialise_value(
                route
            ),
            "plan": self._serialise_value(
                plan
            ),
            "execution": self._serialise_value(
                execution
            ),
            "sources": self._serialise_value(
                sources
            ),
            "tool_result": self._serialise_value(
                tool_result
            ),
            "skill": self._serialise_value(
                skill
            ),
        }

        messages = [
            {
                "role": "user",
                "content": json.dumps(
                    review_payload,
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        ]

        try:
            raw_response = self._call_model(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=0.0,
            )

            parsed = self._parse_json_object(
                raw_response
            )

            review = (
                self._normalise_review_payload(
                    parsed
                )
            )

            report = self._create_report(
                user_request=cleaned_request,
                original_output=cleaned_output,
                review=review,
                route=route,
                plan=plan,
                execution=execution,
                document_sources=sources,
                tool_result=tool_result,
                skill=skill,
                metadata={
                    "critic_fallback": False,
                },
            )

        except Exception as exc:
            report = (
                self._create_safe_fallback_report(
                    user_request=cleaned_request,
                    original_output=cleaned_output,
                    route=route,
                    plan=plan,
                    execution=execution,
                    document_sources=sources,
                    tool_result=tool_result,
                    skill=skill,
                    reason=str(
                        exc
                    ),
                )
            )

        self.save_report(
            report
        )

        return report

    @classmethod
    def _looks_like_critic_json(
        cls,
        value: str,
    ) -> bool:
        cleaned = cls._strip_code_fences(
            value
        )

        if not cleaned.startswith(
            "{"
        ):
            return False

        try:
            parsed = cls._parse_json_object(
                cleaned
            )

        except ValueError:
            return False

        keys = {
            str(
                key
            )
            for key in parsed
        }

        return bool(
            keys
            & CRITIC_JSON_KEYS
        )

    @staticmethod
    def _contains_internal_markers(
        value: str,
    ) -> bool:
        upper_value = str(
            value or ""
        ).upper()

        return any(
            marker in upper_value
            for marker in INTERNAL_OUTPUT_MARKERS
        )

    @classmethod
    def _extract_revision_text(
        cls,
        raw_response: str,
    ) -> str:
        cleaned = cls._strip_code_fences(
            raw_response
        )

        if not cleaned:
            return ""

        if cleaned.startswith(
            "{"
        ):
            try:
                parsed = cls._parse_json_object(
                    cleaned
                )

            except ValueError:
                return ""

            for key in (
                "revised_answer",
                "revised_output",
                "answer",
                "final_answer",
                "content",
            ):
                candidate = parsed.get(
                    key
                )

                if isinstance(
                    candidate,
                    str,
                ) and candidate.strip():
                    cleaned = candidate.strip()
                    break

            else:
                return ""

        if cls._looks_like_critic_json(
            cleaned
        ):
            return ""

        if cls._contains_internal_markers(
            cleaned
        ):
            return ""

        return cleaned.strip()

    @classmethod
    def _update_report_revision(
        cls,
        report: CriticReport,
        revised_output: str,
    ) -> None:
        attribute_names = (
            "revised_output",
            "revised_answer",
            "final_output",
        )

        for name in attribute_names:
            if hasattr(
                report,
                name,
            ):
                try:
                    setattr(
                        report,
                        name,
                        revised_output,
                    )

                except Exception:
                    pass

        for name in (
            "revision_applied",
            "was_revised",
        ):
            if hasattr(
                report,
                name,
            ):
                try:
                    setattr(
                        report,
                        name,
                        True,
                    )

                except Exception:
                    pass

        if hasattr(
            report,
            "updated_at",
        ):
            try:
                setattr(
                    report,
                    "updated_at",
                    cls._utc_now(),
                )

            except Exception:
                try:
                    setattr(
                        report,
                        "updated_at",
                        cls._utc_now()
                        .isoformat(),
                    )

                except Exception:
                    pass

    def revise_output(
        self,
        *,
        report: CriticReport,
        model: str,
        document_sources: list[
            dict[str, Any]
        ] | None = None,
        tool_result: Any = None,
        **_: Any,
    ) -> str:
        original_output = str(
            self._get_report_value(
                report,
                (
                    "original_output",
                    "original_answer",
                    "output",
                ),
                "",
            )
            or ""
        ).strip()

        if not original_output:
            raise CriticError(
                "The critic report does not contain "
                "an original answer."
            )

        user_request = str(
            self._get_report_value(
                report,
                (
                    "user_request",
                    "request",
                    "prompt",
                ),
                "",
            )
            or ""
        ).strip()

        findings = self._get_report_value(
            report,
            (
                "findings",
                "critic_findings",
                "issues",
            ),
            [],
        )

        summary = str(
            self._get_report_value(
                report,
                (
                    "summary",
                    "critic_summary",
                ),
                "",
            )
            or ""
        ).strip()

        sources = [
            source
            for source in (
                document_sources
                or []
            )
            if isinstance(
                source,
                dict,
            )
        ]

        system_prompt = """
You are the revision stage for TechCorp AI.

Rewrite the answer so it addresses the critic findings while
remaining faithful to the user's request and supplied evidence.

Output only the final natural-language answer.

Rules:

- Do not output JSON.
- Do not output a critic report.
- Do not mention the critic or revision process.
- Do not include STEP COMPLETE, PLAN GOAL UPDATE,
  CURRENT STEP COMPLETE or NEXT STEP.
- Do not invent URLs, sources, facts or tool results.
- Use only exact URLs present in supplied evidence.
- Preserve correct content from the original answer.
- When evidence is insufficient, state the limitation.
- Do not expose private chain-of-thought.
""".strip()

        revision_payload = {
            "user_request": user_request,
            "original_answer": original_output,
            "critic_summary": summary,
            "critic_findings": (
                self._serialise_value(
                    findings
                )
            ),
            "sources": self._serialise_value(
                sources
            ),
            "tool_result": self._serialise_value(
                tool_result
            ),
        }

        messages = [
            {
                "role": "user",
                "content": json.dumps(
                    revision_payload,
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        ]

        try:
            raw_response = self._call_model(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=0.1,
            )

            revised_output = (
                self._extract_revision_text(
                    raw_response
                )
            )

        except Exception:
            return original_output

        if not revised_output:
            return original_output

        self._update_report_revision(
            report,
            revised_output,
        )

        self.save_report(
            report
        )

        return revised_output

    def save_report(
        self,
        report: CriticReport,
    ) -> Path:
        report_data = self._serialise_value(
            self._report_to_dict(
                report
            )
        )

        report_id = str(
            report_data.get(
                "id",
                "",
            )
        ).strip()

        if not report_id:
            report_id = str(
                uuid.uuid4()
            )

            report_data[
                "id"
            ] = report_id

        path = (
            self.report_folder
            / f"{report_id}.json"
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        with self._lock:
            temporary_path.write_text(
                json.dumps(
                    report_data,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                path
            )

        return path

    def load_report(
        self,
        report_id: str,
    ) -> CriticReport | None:
        cleaned_id = str(
            report_id or ""
        ).strip()

        if not cleaned_id:
            return None

        path = (
            self.report_folder
            / f"{cleaned_id}.json"
        )

        if not path.exists():
            return None

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise CriticError(
                f"Could not read critic report "
                f"{cleaned_id}: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise CriticError(
                f"Critic report {cleaned_id} "
                "does not contain a JSON object."
            )

        return self._construct_report(
            payload
        )

    def list_recent_reports(
        self,
        *,
        limit: int = 30,
    ) -> list[CriticReport]:
        safe_limit = max(
            1,
            int(
                limit
            ),
        )

        files = sorted(
            self.report_folder.glob(
                "*.json"
            ),
            key=lambda path: (
                path.stat().st_mtime
            ),
            reverse=True,
        )

        reports: list[
            CriticReport
        ] = []

        for path in files:
            if len(
                reports
            ) >= safe_limit:
                break

            try:
                payload = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                if not isinstance(
                    payload,
                    dict,
                ):
                    continue

                reports.append(
                    self._construct_report(
                        payload
                    )
                )

            except Exception:
                continue

        return reports

    def list_reports(
        self,
        *,
        limit: int = 30,
    ) -> list[CriticReport]:
        return self.list_recent_reports(
            limit=limit
        )

    def delete_report(
        self,
        report_id: str,
    ) -> bool:
        cleaned_id = str(
            report_id or ""
        ).strip()

        if not cleaned_id:
            return False

        path = (
            self.report_folder
            / f"{cleaned_id}.json"
        )

        if not path.exists():
            return False

        try:
            path.unlink()

        except OSError as exc:
            raise CriticError(
                f"Could not delete critic report: {exc}"
            ) from exc

        return True

    def clear_reports(
        self,
    ) -> int:
        deleted = 0

        with self._lock:
            for path in self.report_folder.glob(
                "*.json"
            ):
                try:
                    path.unlink()
                    deleted += 1

                except OSError:
                    continue

        return deleted
