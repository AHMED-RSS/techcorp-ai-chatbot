from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.providers import AIProvider
from core.providers.base import ChatMessage


class FakeAIProvider(AIProvider):
    """
    Lightweight fake provider for tests.
    Avoids dependency on real AI backends.
    """

    def __init__(self) -> None:
        self.chat_calls: list[list[ChatMessage]] = []
        self.embed_calls: list[str] = []

    def chat(
        self,
        messages: Iterable[ChatMessage],
        **kwargs: Any,
    ) -> str:
        self.chat_calls.append(list(messages))
        return "fake response"

    def embed(
        self,
        text: str,
        **kwargs: Any,
    ) -> list[float]:
        self.embed_calls.append(text)
        return [0.1, 0.2, 0.3]

    def health_check(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return ["fake-model"]
