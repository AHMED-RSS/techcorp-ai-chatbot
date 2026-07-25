from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_CRITIC_SEVERITIES = {
    "info",
    "warning",
    "error",
    "critical",
}


VALID_CRITIC_CATEGORIES = {
    "accuracy",
    "grounding",
    "completeness",
    "clarity",
    "consistency",
    "tool_use",
    "instruction_following",
    "safety",
    "other",
}


@dataclass(slots=True)
class CriticFinding:
    """
    One issue discovered by the local critic.
    """

    category: str
    severity: str
    message: str
    recommendation: str = ""
    evidence: str = ""

    def __post_init__(self) -> None:
        cleaned_category = str(
            self.category or "other"
        ).strip().lower()

        if cleaned_category not in VALID_CRITIC_CATEGORIES:
            cleaned_category = "other"

        self.category = cleaned_category

        cleaned_severity = str(
            self.severity or "warning"
        ).strip().lower()

        if cleaned_severity not in VALID_CRITIC_SEVERITIES:
            cleaned_severity = "warning"

        self.severity = cleaned_severity

        self.message = str(
            self.message or ""
        ).strip()[:1_500]

        self.recommendation = str(
            self.recommendation or ""
        ).strip()[:1_500]

        self.evidence = str(
            self.evidence or ""
        ).strip()[:1_500]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
        }


@dataclass(slots=True)
class CriticReport:
    """
    Structured review of one assistant response.
    """

    id: str
    user_request: str
    original_output: str
    passed: bool
    requires_revision: bool
    score: float
    summary: str
    findings: list[CriticFinding] = field(
        default_factory=list
    )
    strengths: list[str] = field(
        default_factory=list
    )
    revised_output: str = ""
    created_at: str = ""
    model: str | None = None
    source: str = "ollama"
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.user_request = str(
            self.user_request or ""
        ).strip()

        self.original_output = str(
            self.original_output or ""
        ).strip()

        self.passed = bool(
            self.passed
        )

        self.requires_revision = bool(
            self.requires_revision
        )

        try:
            numeric_score = float(
                self.score
            )

        except (
            TypeError,
            ValueError,
        ):
            numeric_score = 0.0

        self.score = max(
            0.0,
            min(
                1.0,
                numeric_score,
            ),
        )

        self.summary = str(
            self.summary or ""
        ).strip()[:2_000]

        self.findings = [
            finding
            if isinstance(
                finding,
                CriticFinding,
            )
            else critic_finding_from_dict(
                finding
            )
            for finding in self.findings
            if isinstance(
                finding,
                (CriticFinding, dict),
            )
        ]

        if not isinstance(
            self.strengths,
            list,
        ):
            self.strengths = []

        self.strengths = [
            str(strength).strip()
            for strength in self.strengths
            if str(strength).strip()
        ][:20]

        self.revised_output = str(
            self.revised_output or ""
        ).strip()

        self.created_at = str(
            self.created_at or ""
        )

        if self.model is not None:
            self.model = str(
                self.model
            )

        self.source = str(
            self.source or "ollama"
        ).strip()

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    @property
    def error_count(self) -> int:
        return sum(
            1
            for finding in self.findings
            if finding.severity
            in {
                "error",
                "critical",
            }
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for finding in self.findings
            if finding.severity
            == "warning"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "original_output": self.original_output,
            "passed": self.passed,
            "requires_revision": self.requires_revision,
            "score": self.score,
            "summary": self.summary,
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "strengths": self.strengths,
            "revised_output": self.revised_output,
            "created_at": self.created_at,
            "model": self.model,
            "source": self.source,
            "metadata": self.metadata,
        }


def critic_finding_from_dict(
    data: dict[str, Any],
) -> CriticFinding:
    return CriticFinding(
        category=str(
            data.get(
                "category",
                "other",
            )
        ),
        severity=str(
            data.get(
                "severity",
                "warning",
            )
        ),
        message=str(
            data.get(
                "message",
                "",
            )
        ),
        recommendation=str(
            data.get(
                "recommendation",
                "",
            )
        ),
        evidence=str(
            data.get(
                "evidence",
                "",
            )
        ),
    )


def critic_report_from_dict(
    data: dict[str, Any],
) -> CriticReport:
    return CriticReport(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        user_request=str(
            data.get(
                "user_request",
                "",
            )
        ),
        original_output=str(
            data.get(
                "original_output",
                "",
            )
        ),
        passed=bool(
            data.get(
                "passed",
                False,
            )
        ),
        requires_revision=bool(
            data.get(
                "requires_revision",
                False,
            )
        ),
        score=data.get(
            "score",
            0.0,
        ),
        summary=str(
            data.get(
                "summary",
                "",
            )
        ),
        findings=[
            critic_finding_from_dict(
                finding
            )
            for finding in data.get(
                "findings",
                [],
            )
            if isinstance(
                finding,
                dict,
            )
        ],
        strengths=(
            data.get(
                "strengths",
                [],
            )
        ),
        revised_output=str(
            data.get(
                "revised_output",
                "",
            )
        ),
        created_at=str(
            data.get(
                "created_at",
                "",
            )
        ),
        model=(
            data.get(
                "model"
            )
        ),
        source=str(
            data.get(
                "source",
                "ollama",
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )