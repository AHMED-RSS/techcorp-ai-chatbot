from __future__ import annotations

import json
import math
import re
from typing import Any

from agents.router import RouteDecision


ALLOWED_ROUTES = {
    "general",
    "document",
    "code",
    "study",
    "tool",
}


ROUTE_SKILLS = {
    "general": "general_assistant",
    "document": "document_analyst",
    "code": "code_reviewer",
    "study": "study_coach",
    "tool": "general_assistant",
}


DOCUMENT_TERMS = (
    "attached file",
    "attached document",
    "uploaded file",
    "uploaded document",
    "my document",
    "my documents",
    "the document",
    "the file",
    "these files",
    "search documents",
    "search my documents",
    "document source",
    "document sources",
    "pdf",
    "spreadsheet",
    "presentation",
)


CODE_TERMS = (
    "code",
    "python",
    "javascript",
    "typescript",
    "java ",
    "c++",
    "c#",
    "golang",
    "rust ",
    "html",
    "css",
    "sql",
    "debug",
    "traceback",
    "exception",
    "function",
    "class ",
    "method ",
    "source code",
    "code review",
    "refactor",
    "compile",
    "syntax error",
)


STUDY_TERMS = (
    "study",
    "quiz",
    "flashcard",
    "flashcards",
    "revision",
    "revise for",
    "exam",
    "practice questions",
    "test me",
    "teach me",
    "learning plan",
    "study plan",
    "lesson",
)


TOOL_TERMS = (
    "/tool ",
    "use the calculator",
    "calculate ",
    "evaluate ",
    "current date",
    "current time",
    "list project files",
    "list the files",
    "read the file",
    "open the file",
    "save a report",
    "run the tool",
)


class RouterService:
    """
    Select an agent route using deterministic rules and local Ollama.

    Invalid model output always falls back to a usable general route
    with 50% confidence rather than returning zero confidence.
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
                for attribute in required_attributes
            ):
                return value

        return None

    @staticmethod
    def _normalise_prompt(
        prompt: str,
    ) -> str:
        return " ".join(
            str(
                prompt or ""
            )
            .casefold()
            .split()
        )

    @staticmethod
    def _normalise_skill(
        value: Any,
    ) -> str | None:
        cleaned = str(
            value or ""
        ).strip()

        if not cleaned:
            return None

        cleaned = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            cleaned,
        )

        return cleaned.strip(
            "_"
        ) or None

    @staticmethod
    def _normalise_route(
        value: Any,
    ) -> str:
        cleaned = str(
            value or ""
        ).strip().casefold()

        aliases = {
            "chat": "general",
            "assistant": "general",
            "research": "general",
            "web": "general",
            "rag": "document",
            "documents": "document",
            "files": "document",
            "coding": "code",
            "programming": "code",
            "education": "study",
            "learning": "study",
            "tools": "tool",
            "utility": "tool",
        }

        cleaned = aliases.get(
            cleaned,
            cleaned,
        )

        if cleaned not in ALLOWED_ROUTES:
            return "general"

        return cleaned

    @staticmethod
    def _normalise_confidence(
        value: Any,
        *,
        default: float = 0.5,
    ) -> float:
        try:
            confidence = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return default

        if not math.isfinite(
            confidence
        ):
            return default

        if confidence > 1.0 and confidence <= 100.0:
            confidence /= 100.0

        if confidence < 0.0 or confidence > 1.0:
            return default

        return confidence

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
            for key in (
                "content",
                "response",
                "text",
            ):
                value = response.get(
                    key
                )

                if isinstance(
                    value,
                    str,
                ) and value.strip():
                    return value.strip()

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

    @staticmethod
    def _parse_json_object(
        value: str,
    ) -> dict[str, Any]:
        cleaned = str(
            value or ""
        ).strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        ).strip()

        if not cleaned:
            raise ValueError(
                "The router returned an empty response."
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
            "The router response did not contain valid JSON."
        )

    @staticmethod
    def _contains_any(
        text: str,
        terms: tuple[str, ...],
    ) -> bool:
        return any(
            term in text
            for term in terms
        )

    def _heuristic_decision(
        self,
        prompt: str,
        *,
        has_documents: bool,
        selected_skill: str | None,
    ) -> RouteDecision | None:
        cleaned = self._normalise_prompt(
            prompt
        )

        if not cleaned:
            return self._fallback_decision(
                reason=(
                    "The request was empty, so the general "
                    "fallback route was used."
                ),
                selected_skill=selected_skill,
            )

        if self._contains_any(
            cleaned,
            TOOL_TERMS,
        ):
            return self._build_decision(
                route="tool",
                confidence=0.92,
                reason=(
                    "The request directly asks for a local "
                    "tool or utility operation."
                ),
                selected_skill=selected_skill,
                use_documents=False,
                source="heuristic",
            )

        if self._contains_any(
            cleaned,
            STUDY_TERMS,
        ):
            return self._build_decision(
                route="study",
                confidence=0.88,
                reason=(
                    "The request is primarily a learning or "
                    "study activity."
                ),
                selected_skill=selected_skill,
                use_documents=has_documents,
                source="heuristic",
            )

        if self._contains_any(
            cleaned,
            CODE_TERMS,
        ):
            return self._build_decision(
                route="code",
                confidence=0.86,
                reason=(
                    "The request is primarily about source "
                    "code or software development."
                ),
                selected_skill=selected_skill,
                use_documents=False,
                source="heuristic",
            )

        if (
            has_documents
            and self._contains_any(
                cleaned,
                DOCUMENT_TERMS,
            )
        ):
            return self._build_decision(
                route="document",
                confidence=0.90,
                reason=(
                    "The request explicitly refers to an "
                    "uploaded or indexed local document."
                ),
                selected_skill=selected_skill,
                use_documents=True,
                source="heuristic",
            )

        return None

    def _build_decision(
        self,
        *,
        route: str,
        confidence: float,
        reason: str,
        selected_skill: str | None,
        use_documents: bool,
        source: str,
        recommended_skill: str | None = None,
    ) -> RouteDecision:
        normalised_route = self._normalise_route(
            route
        )

        skill = (
            self._normalise_skill(
                recommended_skill
            )
            or self._normalise_skill(
                selected_skill
            )
            or ROUTE_SKILLS[
                normalised_route
            ]
        )

        return RouteDecision(
            route=normalised_route,
            confidence=self._normalise_confidence(
                confidence,
                default=0.5,
            ),
            reason=(
                str(
                    reason or ""
                ).strip()
                or "The request was routed successfully."
            ),
            recommended_skill=skill,
            use_documents=bool(
                use_documents
            ),
            source=str(
                source or "router"
            ),
        )

    def _fallback_decision(
        self,
        *,
        reason: str,
        selected_skill: str | None,
    ) -> RouteDecision:
        return self._build_decision(
            route="general",
            confidence=0.5,
            reason=reason,
            selected_skill=selected_skill,
            use_documents=False,
            source="fallback",
        )

    def _call_model(
        self,
        *,
        prompt: str,
        has_documents: bool,
        model: str,
    ) -> dict[str, Any]:
        if self.ai is None:
            raise RuntimeError(
                "No Ollama service is configured."
            )

        chat_method = getattr(
            self.ai,
            "chat",
            None,
        )

        if not callable(
            chat_method
        ):
            raise RuntimeError(
                "The Ollama service has no chat method."
            )

        system_prompt = """
You are the internal request router for a local AI application.

Choose exactly one route:

- general: normal conversation, explanation, research or web-grounded answer
- document: questions that require uploaded or indexed local documents
- code: programming, debugging, code review or software development
- study: quizzes, flashcards, lessons, revision or learning activities
- tool: an explicit local utility or tool operation

Return exactly one JSON object:

{
  "route": "general",
  "confidence": 0.75,
  "reason": "Brief routing reason",
  "recommended_skill": "general_assistant",
  "use_documents": false
}

Rules:

- confidence must be between 0.0 and 1.0.
- Do not use document unless local documents are available.
- Web research belongs to general, not document.
- A short factual question normally belongs to general.
- Do not include Markdown or any text outside the JSON object.
""".strip()

        user_payload = {
            "request": prompt,
            "local_documents_available": (
                has_documents
            ),
        }

        messages = [
            {
                "role": "user",
                "content": json.dumps(
                    user_payload,
                    ensure_ascii=False,
                    indent=2,
                ),
            }
        ]

        try:
            response = chat_method(
                messages=messages,
                model=model,
                temperature=0.0,
                system_prompt=system_prompt,
            )

        except TypeError:
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
                    "temperature": 0.0,
                },
            )

        text = self._extract_response_text(
            response
        )

        return self._parse_json_object(
            text
        )

    def route(
        self,
        prompt: str,
        *,
        has_documents: bool = False,
        automatic_skill_selection: bool = True,
        selected_skill: str | None = None,
        model: str | None = None,
        **_: Any,
    ) -> RouteDecision:
        cleaned_prompt = str(
            prompt or ""
        ).strip()

        selected = self._normalise_skill(
            selected_skill
        )

        heuristic = self._heuristic_decision(
            cleaned_prompt,
            has_documents=bool(
                has_documents
            ),
            selected_skill=selected,
        )

        if heuristic is not None:
            if (
                not automatic_skill_selection
                and selected
            ):
                heuristic.recommended_skill = (
                    selected
                )

            return heuristic

        selected_model = str(
            model
            or getattr(
                self.settings,
                "ollama_chat_model",
                ""
            )
            or ""
        ).strip()

        if not selected_model:
            return self._fallback_decision(
                reason=(
                    "No routing model was configured, so the "
                    "general fallback route was used."
                ),
                selected_skill=selected,
            )

        try:
            parsed = self._call_model(
                prompt=cleaned_prompt,
                has_documents=bool(
                    has_documents
                ),
                model=selected_model,
            )

        except Exception as exc:
            return self._fallback_decision(
                reason=(
                    "The router model could not produce a valid "
                    f"decision, so the general fallback was used: {exc}"
                ),
                selected_skill=selected,
            )

        route_name = self._normalise_route(
            parsed.get(
                "route",
                "general",
            )
        )

        use_documents = bool(
            parsed.get(
                "use_documents",
                False,
            )
        )

        if not has_documents:
            use_documents = False

            if route_name == "document":
                route_name = "general"

        confidence = self._normalise_confidence(
            parsed.get(
                "confidence"
            ),
            default=0.5,
        )

        if confidence == 0.0:
            confidence = 0.5

        recommended_skill = (
            self._normalise_skill(
                parsed.get(
                    "recommended_skill"
                )
            )
        )

        if (
            not automatic_skill_selection
            and selected
        ):
            recommended_skill = selected

        return self._build_decision(
            route=route_name,
            confidence=confidence,
            reason=str(
                parsed.get(
                    "reason",
                    "The request was classified by the local router.",
                )
            ),
            selected_skill=selected,
            recommended_skill=recommended_skill,
            use_documents=use_documents,
            source="model",
        )
