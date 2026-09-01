from pathlib import Path

from core.providers import AIProvider
from config.settings import Settings
from services.file_service import FileService
from services.rag_service import RAGService
from services.skill_service import SkillService
from tools.local_tools import build_local_tool_service


class FakeProvider(AIProvider):

    def chat(self, messages, **kwargs):
        return "ok"

    def embed(self, text, **kwargs):
        return [0.0]

    def health_check(self):
        return True

    def list_models(self):
        return []


def test_vision_tools_registered(tmp_path):
    settings = Settings(
        chroma_folder=tmp_path / "chroma",
        agent_run_folder=tmp_path / "runs",
    )

    file_service = FileService(
        settings=settings,
    )

    rag_service = RAGService(
        settings=settings,
        ai_provider=FakeProvider(),
    )

    skill_service = SkillService(
        settings=settings,
    )

    tool_service = build_local_tool_service(
        settings=settings,
        file_service=file_service,
        rag_service=rag_service,
        skill_service=skill_service,
        ai_provider=FakeProvider(),
    )

    tools = {
        tool.name
        for tool in tool_service.list_tools()
    }

    assert "image_analysis" in tools
    assert "chart_analysis" in tools
    assert "image_compare" in tools
