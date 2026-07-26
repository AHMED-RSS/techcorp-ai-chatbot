from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ROUTE_NAMES = {
    "general",
    "document",
    "code",
    "study",
    "tool",
    "vision",
}


DOCUMENT_WORDS = {
    "pdf",
    "document",
    "file",
    "report",
    "paper",
    "uploaded",
    "according to",
    "from the document",
    "summarize",
    "extract",
    "chapter",
    "page",
}


CODE_WORDS = {
    "python",
    "code",
    "bug",
    "error",
    "function",
    "class",
    "api",
    "script",
    "debug",
}


STUDY_WORDS = {
    "study",
    "learn",
    "explain",
    "flashcards",
    "quiz",
    "notes",
    "summary",
    "teach",
}


TOOL_WORDS = {
    "search",
    "calculate",
    "convert",
    "generate",
    "create",
}


VISION_WORDS = {
    "image",
    "photo",
    "picture",
    "chart",
    "graph",
    "screenshot",
    "diagram",
}


@dataclass(slots=True)
class RouteDecision:


    route: str

    confidence: float

    reason: str


    recommended_skill: str | None = None

    tool_name: str | None = None


    tool_arguments: dict[str, Any] = field(
        default_factory=dict
    )


    use_documents: bool = False


    source: str = "router"



    def __post_init__(self):

        self.route = (
            str(self.route)
            .lower()
            .strip()
        )


        if self.route not in VALID_ROUTE_NAMES:

            self.route = "general"



        self.confidence = max(
            0.0,
            min(
                1.0,
                float(self.confidence)
            )
        )


        self.reason = str(
            self.reason
        )



        self.use_documents = bool(
            self.use_documents
        )




    @property
    def wants_tool(self):

        return (
            self.route == "tool"
            and self.tool_name
        )



    def to_dict(self):

        return {

            "route": self.route,

            "confidence": self.confidence,

            "reason": self.reason,

            "recommended_skill":
                self.recommended_skill,

            "tool_name":
                self.tool_name,

            "tool_arguments":
                self.tool_arguments,

            "use_documents":
                self.use_documents,

            "source":
                self.source,

        }




def detect_route(
        query: str
) -> RouteDecision:


    text = query.lower()



    scores = {


        "document": 0,

        "code": 0,

        "study": 0,

        "tool": 0,

        "vision": 0,


    }



    for word in DOCUMENT_WORDS:

        if word in text:

            scores["document"] += 1



    for word in CODE_WORDS:

        if word in text:

            scores["code"] += 1



    for word in STUDY_WORDS:

        if word in text:

            scores["study"] += 1



    for word in TOOL_WORDS:

        if word in text:

            scores["tool"] += 1



    for word in VISION_WORDS:

        if word in text:

            scores["vision"] += 1




    best_route = max(
        scores,
        key=scores.get
    )



    score = scores[best_route]



    if score == 0:


        return RouteDecision(

            route="general",

            confidence=0.55,

            reason="General conversation",

            source="keyword_router"

        )



    confidence = min(

        0.95,

        0.60 + (
            score * 0.08
        )

    )



    skills = {


        "document":
            "document_analysis",


        "code":
            "coding_assistant",


        "study":
            "study_helper",


        "tool":
            "tool_execution",


        "vision":
            "image_analysis",

    }



    return RouteDecision(

        route=best_route,

        confidence=confidence,

        reason=f"Detected {best_route} intent",

        recommended_skill=
            skills.get(best_route),

        use_documents=
            best_route == "document",

        source="keyword_router"

    )





def route_from_dict(

        data: dict[str, Any],

        *,

        source: str,

):


    return RouteDecision(

        route=data.get(
            "route",
            "general"
        ),

        confidence=data.get(
            "confidence",
            0
        ),

        reason=data.get(
            "reason",
            ""
        ),

        recommended_skill=data.get(
            "recommended_skill"
        ),

        tool_name=data.get(
            "tool_name"
        ),

        tool_arguments=data.get(
            "tool_arguments",
            {}
        ),

        use_documents=data.get(
            "use_documents",
            False
        ),

        source=source

    )