from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import uuid


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
    One issue discovered by the critic.
    """

    category: str

    severity: str

    message: str

    recommendation: str = ""

    evidence: str = ""



    def __post_init__(self):

        category = str(
            self.category or "other"
        ).strip().lower()


        if category not in VALID_CRITIC_CATEGORIES:
            category = "other"


        self.category = category



        severity = str(
            self.severity or "warning"
        ).strip().lower()


        if severity not in VALID_CRITIC_SEVERITIES:
            severity = "warning"


        self.severity = severity



        self.message = str(
            self.message or ""
        ).strip()[:1500]


        self.recommendation = str(
            self.recommendation or ""
        ).strip()[:1500]


        self.evidence = str(
            self.evidence or ""
        ).strip()[:1500]



    def to_dict(self):

        return {

            "category":
                self.category,

            "severity":
                self.severity,

            "message":
                self.message,

            "recommendation":
                self.recommendation,

            "evidence":
                self.evidence,

        }





@dataclass(slots=True)
class CriticReport:
    """
    Structured evaluation result.
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


    source: str = "local_critic"


    metadata: dict[str, Any] = field(
        default_factory=dict
    )



    def __post_init__(self):

        self.id = str(
            self.id or ""
        )


        self.user_request = str(
            self.user_request or ""
        )


        self.original_output = str(
            self.original_output or ""
        )


        self.score = max(
            0.0,
            min(
                1.0,
                float(self.score)
            )
        )



        self.findings = [

            finding
            if isinstance(
                finding,
                CriticFinding
            )

            else critic_finding_from_dict(
                finding
            )

            for finding in self.findings

            if isinstance(
                finding,
                (
                    CriticFinding,
                    dict
                )
            )

        ]



    @property
    def error_count(self):

        return sum(

            1

            for finding in self.findings

            if finding.severity
            in {
                "error",
                "critical"
            }

        )



    @property
    def warning_count(self):

        return sum(

            1

            for finding in self.findings

            if finding.severity
            ==
            "warning"

        )



    def to_dict(self):

        return {

            "id":
                self.id,

            "user_request":
                self.user_request,

            "original_output":
                self.original_output,

            "passed":
                self.passed,

            "requires_revision":
                self.requires_revision,

            "score":
                self.score,

            "summary":
                self.summary,

            "findings":
                [
                    f.to_dict()
                    for f in self.findings
                ],

            "strengths":
                self.strengths,

            "revised_output":
                self.revised_output,

            "created_at":
                self.created_at,

            "model":
                self.model,

            "source":
                self.source,

            "metadata":
                self.metadata,

        }





def critic_finding_from_dict(
    data: dict[str, Any]
):

    return CriticFinding(

        category=data.get(
            "category",
            "other"
        ),

        severity=data.get(
            "severity",
            "warning"
        ),

        message=data.get(
            "message",
            ""
        ),

        recommendation=data.get(
            "recommendation",
            ""
        ),

        evidence=data.get(
            "evidence",
            ""
        )

    )





def critic_report_from_dict(
    data: dict[str, Any]
):

    return CriticReport(

        id=data.get(
            "id",
            ""
        ),

        user_request=data.get(
            "user_request",
            ""
        ),

        original_output=data.get(
            "original_output",
            ""
        ),

        passed=data.get(
            "passed",
            False
        ),

        requires_revision=data.get(
            "requires_revision",
            False
        ),

        score=data.get(
            "score",
            0
        ),

        summary=data.get(
            "summary",
            ""
        ),

        findings=[
            critic_finding_from_dict(x)
            for x in data.get(
                "findings",
                []
            )
        ],

        strengths=data.get(
            "strengths",
            []
        ),

        revised_output=data.get(
            "revised_output",
            ""
        ),

        created_at=data.get(
            "created_at",
            ""
        ),

        model=data.get(
            "model"
        ),

        source=data.get(
            "source",
            "local_critic"
        ),

        metadata=data.get(
            "metadata",
            {}
        )

    )





def evaluate_response(
    user_request: str,
    response: str,
    *,
    context: str = "",
    model: str | None = None,
):
    """
    Critic Agent.

    Checks:
    - completeness
    - grounding
    - clarity
    - quality
    """


    findings = []

    strengths = []

    score = 1.0



    if not response.strip():

        findings.append(

            CriticFinding(

                category="completeness",

                severity="critical",

                message=
                "Response is empty.",

                recommendation=
                "Generate a complete response."

            )

        )

        score -= 0.5

    else:

        strengths.append(
            "Response contains information."
        )



    if len(response.split()) < 10:

        findings.append(

            CriticFinding(

                category="completeness",

                severity="warning",

                message=
                "Response may lack detail.",

                recommendation=
                "Expand explanation."

            )

        )

        score -= 0.1



    if context:

        response_words = set(
            response.lower().split()
        )

        context_words = set(
            context.lower().split()
        )


        overlap = (

            len(
                response_words
                &
                context_words
            )

            /

            max(
                len(response_words),
                1
            )

        )


        if overlap < 0.05:

            findings.append(

                CriticFinding(

                    category="grounding",

                    severity="warning",

                    message=
                    "Weak grounding with supplied context.",

                    recommendation=
                    "Use retrieved information."

                )

            )

            score -= 0.15


        else:

            strengths.append(
                "Response uses context."
            )



    score = max(
        0,
        min(
            1,
            score
        )
    )



    passed = (

        score >= 0.75

        and

        not any(

            f.severity
            in {
                "error",
                "critical"
            }

            for f in findings

        )

    )



    return CriticReport(

        id=
        f"critic_{uuid.uuid4().hex[:8]}",

        user_request=
        user_request,

        original_output=
        response,

        passed=
        passed,

        requires_revision=
        not passed,

        score=
        score,

        summary=(

            "Response passed review."

            if passed

            else

            "Response requires revision."

        ),

        findings=
        findings,

        strengths=
        strengths,

        created_at=
        datetime.utcnow()
        .isoformat(),

        model=
        model,

        source=
        "local_critic"

    )