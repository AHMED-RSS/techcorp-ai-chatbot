from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.ollama_client import OllamaManager
from core.providers.base import (
    AIProvider,
    ChatMessage,
)


class OllamaProvider(AIProvider):
    """
    Ollama implementation of the AI provider interface.
    """

    def __init__(
        self,
        ollama_manager: OllamaManager,
    ) -> None:
        self.ollama = ollama_manager

    def chat(
        self,
        messages: Iterable[ChatMessage],
        **kwargs: Any,
    ) -> str:
        return self.ollama.chat(
            messages,
            **kwargs,
        )

    def embed(
        self,
        text: str,
        **kwargs: Any,
    ) -> list[float]:
        return self.ollama.embed(
            text,
            **kwargs,
        )

    def health_check(self) -> bool:
        return self.ollama.health_check()

    def list_models(self) -> list[str]:
        return self.ollama.list_models()
