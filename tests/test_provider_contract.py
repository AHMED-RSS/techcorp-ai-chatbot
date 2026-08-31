from __future__ import annotations

from core.providers import (
    AIProvider,
    OllamaProvider,
)


def test_ollama_provider_implements_ai_provider() -> None:
    assert issubclass(
        OllamaProvider,
        AIProvider,
    )