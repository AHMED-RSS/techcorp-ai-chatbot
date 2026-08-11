from __future__ import annotations

import json
import os
import re
import shutil
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.exceptions import SkillError
from core.logging_config import get_logger


logger = get_logger(__name__)


SKILL_MANIFEST_FILENAME = "skill.json"
SKILL_INSTRUCTION_FILENAME = "skill.md"


BUILT_IN_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "slug": "general_assistant",
        "name": "General Assistant",
        "description": (
            "A balanced general-purpose assistant for normal "
            "questions, explanations and writing."
        ),
        "icon": "✨",
        "keywords": [
            "general",
            "question",
            "explain",
            "help",
            "write",
            "brainstorm",
        ],
        "instructions": """
You are a clear and dependable general-purpose assistant.

Guidelines:
- Answer the user's actual request directly.
- Explain difficult ideas in understandable steps.
- Do not claim to use tools, files or web search unless they were provided.
- State uncertainty when information is incomplete.
- Prefer practical answers over unnecessary verbosity.
""".strip(),
    },
    {
        "slug": "document_analyst",
        "name": "Document Analyst",
        "description": (
            "Answers questions from selected local files and "
            "keeps claims grounded in retrieved passages."
        ),
        "icon": "📄",
        "keywords": [
            "document",
            "file",
            "pdf",
            "report",
            "source",
            "summarise",
            "summarize",
            "extract",
            "compare",
        ],
        "instructions": """
You are a document analysis specialist.

Guidelines:
- Ground document-based claims in the supplied local sources.
- Cite supplied source labels such as [Source 1].
- Preserve terminology and distinctions used in the documents.
- Do not invent information that is absent from the sources.
- Clearly state when the selected documents do not contain enough evidence.
- Distinguish document evidence from your own inference.
""".strip(),
    },
    {
        "slug": "code_reviewer",
        "name": "Code Reviewer",
        "description": (
            "Reviews source code for correctness, readability, "
            "security and maintainability."
        ),
        "icon": "💻",
        "keywords": [
            "code",
            "python",
            "javascript",
            "typescript",
            "bug",
            "debug",
            "review",
            "refactor",
            "error",
            "traceback",
        ],
        "instructions": """
You are a senior software engineer performing a code review.

Review priorities:
1. Correctness and runtime errors.
2. Security and unsafe behaviour.
3. Data loss and destructive operations.
4. Maintainability and readability.
5. Performance when relevant.

When proposing code:
- Provide complete usable code where practical.
- Preserve the user's architecture unless a change is necessary.
- Explain the cause of errors, not only the fix.
- Avoid inventing APIs or functions.
""".strip(),
    },
    {
        "slug": "study_coach",
        "name": "Study Coach",
        "description": (
            "Turns local material into explanations, revision "
            "notes, flashcards and practice questions."
        ),
        "icon": "🎓",
        "keywords": [
            "study",
            "learn",
            "quiz",
            "flashcard",
            "revision",
            "exam",
            "summary",
            "notes",
        ],
        "instructions": """
You are a structured study coach.

Guidelines:
- Preserve the terminology and level of detail in supplied study material.
- Explain concepts before testing them.
- Use headings and concise examples.
- For quizzes, avoid revealing the answer before the learner responds.
- For flashcards, keep one clear fact or concept per card.
- Do not add unsupported facts to source-based study material.
""".strip(),
    },
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )


def clean_slug(value: str) -> str:
    cleaned = str(
        value or ""
    ).strip().lower()

    cleaned = re.sub(
        r"[^a-z0-9]+",
        "_",
        cleaned,
    )

    cleaned = re.sub(
        r"_+",
        "_",
        cleaned,
    ).strip("_")

    if not cleaned:
        cleaned = f"skill_{uuid.uuid4().hex[:8]}"

    return cleaned[:60]


def clean_name(value: str) -> str:
    cleaned = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    return cleaned[:80]


def clean_description(value: str) -> str:
    cleaned = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    return cleaned[:300]


def clean_keywords(
    keywords: list[str] | tuple[str, ...] | str,
) -> list[str]:
    if isinstance(keywords, str):
        values = re.split(
            r"[,;\n]+",
            keywords,
        )
    else:
        values = list(keywords)

    result: list[str] = []

    for value in values:
        keyword = re.sub(
            r"\s+",
            " ",
            str(value or ""),
        ).strip().lower()

        if (
            keyword
            and keyword not in result
        ):
            result.append(keyword[:40])

    return result[:30]


@dataclass(slots=True)
class Skill:
    slug: str
    name: str
    description: str
    instructions: str
    icon: str
    keywords: list[str]
    built_in: bool
    enabled: bool
    created_at: str
    updated_at: str
    folder: Path

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "icon": self.icon,
            "keywords": self.keywords,
            "built_in": self.built_in,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "folder": str(self.folder),
        }


class SkillService:
    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings
        self.skills_folder = settings.skills_folder

        self.skills_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ensure_built_in_skills()

    def skill_folder(
        self,
        slug: str,
    ) -> Path:
        safe_slug = clean_slug(slug)

        return self.skills_folder / safe_slug

    def manifest_path(
        self,
        slug: str,
    ) -> Path:
        return (
            self.skill_folder(slug)
            / SKILL_MANIFEST_FILENAME
        )

    def instruction_path(
        self,
        slug: str,
    ) -> Path:
        return (
            self.skill_folder(slug)
            / SKILL_INSTRUCTION_FILENAME
        )

    def ensure_built_in_skills(
        self,
    ) -> None:
        for definition in BUILT_IN_SKILLS:
            slug = definition["slug"]
            folder = self.skill_folder(slug)
            manifest_path = (
                folder / SKILL_MANIFEST_FILENAME
            )
            instruction_path = (
                folder / SKILL_INSTRUCTION_FILENAME
            )

            if (
                manifest_path.exists()
                and instruction_path.exists()
            ):
                continue

            folder.mkdir(
                parents=True,
                exist_ok=True,
            )

            timestamp = utc_now()

            existing_manifest: dict[str, Any] = {}

            if manifest_path.exists():
                try:
                    existing_manifest = json.loads(
                        manifest_path.read_text(
                            encoding="utf-8",
                        )
                    )

                except Exception:
                    logger.warning(
                        "Repairing invalid built-in "
                        "skill manifest: %s",
                        slug,
                    )

            manifest = {
                "schema_version": 1,
                "slug": slug,
                "name": definition["name"],
                "description": (
                    definition["description"]
                ),
                "icon": definition["icon"],
                "keywords": (
                    definition["keywords"]
                ),
                "built_in": True,
                "enabled": bool(
                    existing_manifest.get(
                        "enabled",
                        True,
                    )
                ),
                "created_at": (
                    existing_manifest.get(
                        "created_at",
                        timestamp,
                    )
                ),
                "updated_at": timestamp,
            }

            self._atomic_write_json(
                manifest_path,
                manifest,
            )

            self._atomic_write_text(
                instruction_path,
                definition["instructions"],
            )

    def validate_skill_data(
        self,
        *,
        name: str,
        description: str,
        instructions: str,
        keywords: list[str] | str,
    ) -> dict[str, Any]:
        cleaned_name = clean_name(name)
        cleaned_description = clean_description(
            description
        )
        cleaned_instructions = str(
            instructions or ""
        ).strip()
        cleaned_keyword_list = clean_keywords(
            keywords
        )

        errors: list[str] = []

        if len(cleaned_name) < 2:
            errors.append(
                "Skill name must contain at least "
                "two characters."
            )

        if len(cleaned_description) < 10:
            errors.append(
                "Skill description must contain at "
                "least ten characters."
            )

        if len(cleaned_instructions) < 30:
            errors.append(
                "Skill instructions must contain at "
                "least thirty characters."
            )

        if errors:
            raise SkillError(
                " ".join(errors)
            )

        return {
            "name": cleaned_name,
            "description": cleaned_description,
            "instructions": cleaned_instructions,
            "keywords": cleaned_keyword_list,
        }

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        instructions: str,
        keywords: list[str] | str,
        icon: str = "✨",
        enabled: bool = True,
    ) -> Skill:
        validated = self.validate_skill_data(
            name=name,
            description=description,
            instructions=instructions,
            keywords=keywords,
        )

        slug = clean_slug(
            validated["name"]
        )

        original_slug = slug
        counter = 2

        while self.skill_folder(slug).exists():
            slug = (
                f"{original_slug}_{counter}"
            )
            counter += 1

        timestamp = utc_now()
        folder = self.skill_folder(slug)

        folder.mkdir(
            parents=True,
            exist_ok=False,
        )

        manifest = {
            "schema_version": 1,
            "slug": slug,
            "name": validated["name"],
            "description": (
                validated["description"]
            ),
            "icon": str(icon or "✨")[:4],
            "keywords": validated["keywords"],
            "built_in": False,
            "enabled": bool(enabled),
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        try:
            self._atomic_write_json(
                folder / SKILL_MANIFEST_FILENAME,
                manifest,
            )

            self._atomic_write_text(
                folder / SKILL_INSTRUCTION_FILENAME,
                validated["instructions"],
            )

        except Exception:
            shutil.rmtree(
                folder,
                ignore_errors=True,
            )
            raise

        skill = self.load_skill(slug)

        if skill is None:
            raise SkillError(
                "The skill was created but could "
                "not be loaded."
            )

        return skill

    def update_skill(
        self,
        slug: str,
        *,
        name: str,
        description: str,
        instructions: str,
        keywords: list[str] | str,
        icon: str,
        enabled: bool,
    ) -> Skill:
        existing = self.load_skill(slug)

        if existing is None:
            raise SkillError(
                "Skill was not found."
            )

        validated = self.validate_skill_data(
            name=name,
            description=description,
            instructions=instructions,
            keywords=keywords,
        )

        manifest = {
            "schema_version": 1,
            "slug": existing.slug,
            "name": validated["name"],
            "description": (
                validated["description"]
            ),
            "icon": str(icon or "✨")[:4],
            "keywords": validated["keywords"],
            "built_in": existing.built_in,
            "enabled": bool(enabled),
            "created_at": existing.created_at,
            "updated_at": utc_now(),
        }

        self._atomic_write_json(
            self.manifest_path(existing.slug),
            manifest,
        )

        self._atomic_write_text(
            self.instruction_path(existing.slug),
            validated["instructions"],
        )

        updated = self.load_skill(
            existing.slug
        )

        if updated is None:
            raise SkillError(
                "The skill was updated but could "
                "not be loaded."
            )

        return updated

    def delete_skill(
        self,
        slug: str,
    ) -> bool:
        skill = self.load_skill(slug)

        if skill is None:
            return False

        if skill.built_in:
            raise SkillError(
                "Built-in skills cannot be deleted."
            )

        try:
            shutil.rmtree(
                skill.folder
            )
            return True

        except OSError as exc:
            raise SkillError(
                f"Could not delete skill: {exc}"
            ) from exc

    def load_skill(
        self,
        slug: str,
    ) -> Skill | None:
        folder = self.skill_folder(slug)
        manifest_path = (
            folder / SKILL_MANIFEST_FILENAME
        )
        instruction_path = (
            folder / SKILL_INSTRUCTION_FILENAME
        )

        if (
            not manifest_path.exists()
            or not instruction_path.exists()
        ):
            return None

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8",
                )
            )

            instructions = (
                instruction_path.read_text(
                    encoding="utf-8",
                ).strip()
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise SkillError(
                f"Could not load skill '{slug}': {exc}"
            ) from exc

        return Skill(
            slug=str(
                manifest.get(
                    "slug",
                    slug,
                )
            ),
            name=clean_name(
                manifest.get(
                    "name",
                    slug,
                )
            ),
            description=clean_description(
                manifest.get(
                    "description",
                    "",
                )
            ),
            instructions=instructions,
            icon=str(
                manifest.get(
                    "icon",
                    "✨",
                )
            ),
            keywords=clean_keywords(
                manifest.get(
                    "keywords",
                    [],
                )
            ),
            built_in=bool(
                manifest.get(
                    "built_in",
                    False,
                )
            ),
            enabled=bool(
                manifest.get(
                    "enabled",
                    True,
                )
            ),
            created_at=str(
                manifest.get(
                    "created_at",
                    utc_now(),
                )
            ),
            updated_at=str(
                manifest.get(
                    "updated_at",
                    utc_now(),
                )
            ),
            folder=folder,
        )

    def list_skills(
        self,
        *,
        include_disabled: bool = True,
    ) -> list[Skill]:
        skills: list[Skill] = []

        for folder in self.skills_folder.iterdir():
            if not folder.is_dir():
                continue

            try:
                skill = self.load_skill(
                    folder.name
                )

                if skill is None:
                    continue

                if (
                    not include_disabled
                    and not skill.enabled
                ):
                    continue

                skills.append(skill)

            except SkillError as exc:
                logger.warning(
                    "Skipping invalid skill %s: %s",
                    folder.name,
                    exc,
                )

        skills.sort(
            key=lambda skill: (
                not skill.built_in,
                skill.name.lower(),
            )
        )

        return skills

    def enabled_skills(
        self,
    ) -> list[Skill]:
        return self.list_skills(
            include_disabled=False
        )

    def match_skill(
        self,
        prompt: str,
        *,
        has_documents: bool = False,
    ) -> Skill:
        cleaned_prompt = str(
            prompt or ""
        ).strip().lower()

        skills = self.enabled_skills()

        if not skills:
            raise SkillError(
                "No enabled skills are available."
            )

        scores: dict[str, float] = {
            skill.slug: 0.0
            for skill in skills
        }

        prompt_tokens = set(
            re.findall(
                r"[a-z0-9_+-]+",
                cleaned_prompt,
            )
        )

        for skill in skills:
            searchable_text = " ".join(
                [
                    skill.name,
                    skill.description,
                    *skill.keywords,
                ]
            ).lower()

            searchable_tokens = set(
                re.findall(
                    r"[a-z0-9_+-]+",
                    searchable_text,
                )
            )

            overlap = (
                prompt_tokens
                & searchable_tokens
            )

            scores[skill.slug] += (
                len(overlap) * 2.0
            )

            for keyword in skill.keywords:
                if keyword in cleaned_prompt:
                    scores[skill.slug] += 3.0

            if (
                has_documents
                and skill.slug
                == "document_analyst"
            ):
                scores[skill.slug] += 5.0

            if (
                not has_documents
                and skill.slug
                == "general_assistant"
            ):
                scores[skill.slug] += 1.0

        best_skill = max(
            skills,
            key=lambda skill: scores[
                skill.slug
            ],
        )

        if scores[best_skill.slug] <= 0:
            general = next(
                (
                    skill
                    for skill in skills
                    if skill.slug
                    == "general_assistant"
                ),
                None,
            )

            if general is not None:
                return general

        return best_skill

    def resolve_skill(
        self,
        *,
        prompt: str,
        selected_slug: str | None,
        automatic: bool,
        has_documents: bool,
    ) -> Skill:
        if (
            not automatic
            and selected_slug
        ):
            selected = self.load_skill(
                selected_slug
            )

            if (
                selected is not None
                and selected.enabled
            ):
                return selected

        return self.match_skill(
            prompt,
            has_documents=has_documents,
        )

    @staticmethod
    def build_skill_prompt(
        skill: Skill,
    ) -> str:
        return (
            f"ACTIVE SKILL: {skill.name}\n"
            f"SKILL DESCRIPTION: "
            f"{skill.description}\n\n"
            f"SKILL INSTRUCTIONS:\n"
            f"{skill.instructions}"
        )

    @staticmethod
    def _atomic_write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:
        temporary_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise SkillError(
                f"Could not save skill manifest: {exc}"
            ) from exc

    @staticmethod
    def _atomic_write_text(
        path: Path,
        text: str,
    ) -> None:
        temporary_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        try:
            temporary_path.write_text(
                str(text).strip() + "\n",
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise SkillError(
                f"Could not save skill instructions: {exc}"
            ) from exc