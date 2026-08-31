from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agents_and_services_do_not_import_ollama_directly():
    forbidden = "from core.ollama_client import OllamaManager"

    for folder in ("agents", "services"):
        for path in (PROJECT_ROOT / folder).rglob("*.py"):
            content = path.read_text(
                encoding="utf-8"
            )

            assert forbidden not in content, (
                f"Direct Ollama dependency found in {path}"
            )
