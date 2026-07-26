from __future__ import annotations

from collections.abc import Generator, Iterable, Sequence
from typing import Any

import ollama
from ollama import Client
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import Settings
from core.exceptions import (
    OllamaConnectionError,
    OllamaModelError,
)
from core.logging_config import get_logger


logger = get_logger(__name__)


ChatMessage = dict[str, Any]


class OllamaManager:
    """
    Central local Ollama service.

    Chat, streaming, planning, routing and embeddings should use
    this manager instead of calling Ollama directly.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client = Client(
            host=settings.ollama_host,
            timeout=settings.ollama_request_timeout,
        )

    def health_check(self) -> bool:
        try:
            self.client.list()
            return True

        except Exception as exc:
            logger.warning(
                "Ollama health check failed: %s",
                exc,
            )

            return False

    def list_models(self) -> list[str]:
        try:
            response = self.client.list()

            models = getattr(
                response,
                "models",
                None,
            )

            if (
                models is None
                and isinstance(response, dict)
            ):
                models = response.get(
                    "models",
                    [],
                )

            model_names: list[str] = []

            for model in models or []:
                model_name = getattr(
                    model,
                    "model",
                    None,
                )

                if (
                    not model_name
                    and isinstance(model, dict)
                ):
                    model_name = (
                        model.get("model")
                        or model.get("name")
                    )

                if model_name:
                    model_names.append(
                        str(model_name)
                    )

            return sorted(
                set(model_names)
            )

        except Exception as exc:
            raise OllamaConnectionError(
                "Could not retrieve local Ollama "
                f"models: {exc}"
            ) from exc

    def model_exists(
        self,
        model_name: str,
    ) -> bool:
        available_models = (
            self.list_models()
        )

        if model_name in available_models:
            return True

        requested_base = (
            model_name.split(":")[0]
        )

        return any(
            installed_model.split(":")[0]
            == requested_base
            for installed_model
            in available_models
        )

    def require_model(
        self,
        model_name: str,
    ) -> None:
        if self.model_exists(model_name):
            return

        raise OllamaModelError(
            f"Local model '{model_name}' is not installed. "
            f"Run: ollama pull {model_name}"
        )

    @retry(
        retry=retry_if_exception_type(
            (
                ConnectionError,
                TimeoutError,
                ollama.ResponseError,
            )
        ),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        response_format: (
            str
            | dict[str, Any]
            | None
        ) = None,
    ) -> str:
        selected_model = (
            model
            or self.settings.ollama_chat_model
        )

        prepared_messages = (
            self._prepare_messages(
                messages=messages,
                system_prompt=system_prompt,
            )
        )

        try:
            response = self.client.chat(
                model=selected_model,
                messages=prepared_messages,
                stream=False,
                options={
                    "temperature": (
                        temperature
                        if temperature is not None
                        else self.settings
                        .agent_default_temperature
                    )
                },
                format=response_format,
            )

            response_message = getattr(
                response,
                "message",
                None,
            )

            content = getattr(
                response_message,
                "content",
                None,
            )

            if (
                not content
                and isinstance(response, dict)
            ):
                content = (
                    response
                    .get("message", {})
                    .get("content")
                )

            if not content:
                raise OllamaModelError(
                    "The local model returned "
                    "an empty response."
                )

            return str(content).strip()

        except ollama.ResponseError as exc:
            error_text = getattr(
                exc,
                "error",
                str(exc),
            )

            raise OllamaModelError(
                f"Local model '{selected_model}' "
                f"failed: {error_text}"
            ) from exc

        except OllamaModelError:
            raise

        except Exception as exc:
            raise OllamaConnectionError(
                "Could not communicate with "
                f"local Ollama: {exc}"
            ) from exc

    def stream_chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> Generator[str, None, None]:
        selected_model = (
            model
            or self.settings.ollama_chat_model
        )

        prepared_messages = (
            self._prepare_messages(
                messages=messages,
                system_prompt=system_prompt,
            )
        )

        try:
            stream = self.client.chat(
                model=selected_model,
                messages=prepared_messages,
                stream=True,
                options={
                    "temperature": (
                        temperature
                        if temperature is not None
                        else self.settings
                        .agent_default_temperature
                    )
                },
            )

            for part in stream:
                response_message = getattr(
                    part,
                    "message",
                    None,
                )

                content = getattr(
                    response_message,
                    "content",
                    None,
                )

                if (
                    not content
                    and isinstance(part, dict)
                ):
                    content = (
                        part
                        .get("message", {})
                        .get("content")
                    )

                if content:
                    yield str(content)

        except ollama.ResponseError as exc:
            error_text = getattr(
                exc,
                "error",
                str(exc),
            )

            raise OllamaModelError(
                f"Ollama streaming failed: "
                f"{error_text}"
            ) from exc

        except OllamaModelError:
            raise

        except Exception as exc:
            raise OllamaConnectionError(
                f"Local streaming failed: {exc}"
            ) from exc

    def embed(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        embeddings = self.embed_many(
            texts=[text],
            model=model,
        )

        if not embeddings:
            raise OllamaModelError(
                "The local embedding model "
                "returned no vector."
            )

        return embeddings[0]

    @retry(
        retry=retry_if_exception_type(
            (
                ConnectionError,
                TimeoutError,
                ollama.ResponseError,
            )
        ),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=8,
        ),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def embed_many(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """
        Generate local embeddings for one or more texts.

        Batching improves document indexing performance because Ollama
        can process several chunks in a single request.
        """

        selected_model = (
            model
            or self.settings.ollama_embed_model
        )

        cleaned_texts = [
            str(text).strip()
            for text in texts
            if str(text).strip()
        ]

        if not cleaned_texts:
            return []

        try:
            response = self.client.embed(
                model=selected_model,
                input=cleaned_texts,
            )

            embeddings = getattr(
                response,
                "embeddings",
                None,
            )

            if (
                embeddings is None
                and isinstance(response, dict)
            ):
                embeddings = response.get(
                    "embeddings"
                )

            if not embeddings:
                raise OllamaModelError(
                    "The local embedding model "
                    "returned no vectors."
                )

            vectors = [
                [
                    float(value)
                    for value in vector
                ]
                for vector in embeddings
            ]

            if (
                len(vectors)
                != len(cleaned_texts)
            ):
                raise OllamaModelError(
                    "The number of embedding vectors "
                    "does not match the number of texts."
                )

            return vectors

        except ollama.ResponseError as exc:
            error_text = getattr(
                exc,
                "error",
                str(exc),
            )

            raise OllamaModelError(
                f"Embedding model "
                f"'{selected_model}' failed: "
                f"{error_text}"
            ) from exc

        except OllamaModelError:
            raise

        except Exception as exc:
            raise OllamaConnectionError(
                "Could not create local "
                f"embeddings: {exc}"
            ) from exc

    @staticmethod
    def _prepare_messages(
        messages: Iterable[ChatMessage],
        system_prompt: str | None = None,
    ) -> list[ChatMessage]:
        prepared: list[ChatMessage] = []

        if system_prompt:
            prepared.append(
                {
                    "role": "system",
                    "content": (
                        system_prompt.strip()
                    ),
                }
            )

        for message in messages:
            role = str(
                message.get(
                    "role",
                    "",
                )
            ).strip()

            content = str(
                message.get(
                    "content",
                    "",
                )
            ).strip()

            if role not in {
                "system",
                "user",
                "assistant",
                "tool",
            }:
                continue

            if not content:
                continue

            prepared_message: ChatMessage = {
                "role": role,
                "content": content,
            }

            images = message.get(
                "images"
            )

            if images:
                prepared_message["images"] = (
                    images
                )

            prepared.append(
                prepared_message
            )

        return prepared