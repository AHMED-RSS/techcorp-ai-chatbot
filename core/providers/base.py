from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Iterable


ChatMessage = dict[str, Any]


class AIProvider(ABC):
    """
    Abstract interface for AI model providers.
    """

    @abstractmethod
    def chat(
        self,
        messages: Iterable[ChatMessage],
        **kwargs: Any,
    ) -> str:
        """
        Generate a chat response.
        """
        raise NotImplementedError

    @abstractmethod
    def embed(
        self,
        text: str,
        **kwargs: Any,
    ) -> list[float]:
        """
        Generate an embedding vector.
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check provider availability.
        """
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> list[str]:
        """
        Return available models.
        """
        raise NotImplementedError
