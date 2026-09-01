from pathlib import Path

import pytest

from services.vision_service import (
    VISION_MODEL,
    analyze_chart,
    analyze_document_image,
    analyze_image,
    check_vision_model,
    compare_images,
    describe_image,
)


class FakeVisionProvider:
    def __init__(
        self,
        *,
        models: list[str] | None = None,
        response: str = "vision result",
    ):
        self.models = models or []
        self.response = response
        self.chat_calls: list[dict] = []

    def list_models(self) -> list[str]:
        return list(self.models)

    def chat(
        self,
        messages,
        **kwargs,
    ) -> str:
        self.chat_calls.append(
            {
                "messages": messages,
                **kwargs,
            }
        )
        return self.response


def make_image(
    tmp_path: Path,
    name: str = "image.png",
) -> Path:
    path = tmp_path / name
    path.write_bytes(b"fake-image-data")
    return path


def test_check_vision_model_accepts_provider_model_list():
    provider = FakeVisionProvider(
        models=[
            "llama3.2:latest",
            VISION_MODEL,
        ]
    )

    assert check_vision_model(provider) is True


def test_check_vision_model_returns_false_when_model_missing():
    provider = FakeVisionProvider(
        models=[
            "llama3.2:latest",
        ]
    )

    assert check_vision_model(provider) is False


def test_analyze_image_returns_provider_string(
    tmp_path: Path,
):
    image = make_image(tmp_path)

    provider = FakeVisionProvider(
        response="The image contains a chart."
    )

    result = analyze_image(
        image,
        "What is shown?",
        ai_provider=provider,
    )

    assert result == "The image contains a chart."
    assert len(provider.chat_calls) == 1

    call = provider.chat_calls[0]

    assert call["model"] == VISION_MODEL
    assert call["messages"][0]["role"] == "user"
    assert call["messages"][0]["content"] == "What is shown?"
    assert call["messages"][0]["images"] == [
        str(image)
    ]


@pytest.mark.parametrize(
    "wrapper",
    [
        analyze_chart,
        analyze_document_image,
        describe_image,
    ],
)
def test_single_image_wrappers_forward_provider(
    wrapper,
    tmp_path: Path,
):
    image = make_image(tmp_path)

    provider = FakeVisionProvider(
        response="wrapper result"
    )

    result = wrapper(
        image,
        ai_provider=provider,
    )

    assert result == "wrapper result"
    assert len(provider.chat_calls) == 1

    call = provider.chat_calls[0]

    assert call["model"] == VISION_MODEL
    assert call["messages"][0]["images"] == [
        str(image)
    ]


def test_compare_images_returns_provider_string(
    tmp_path: Path,
):
    image1 = make_image(
        tmp_path,
        "first.png",
    )

    image2 = make_image(
        tmp_path,
        "second.png",
    )

    provider = FakeVisionProvider(
        response="The images are different."
    )

    result = compare_images(
        image1,
        image2,
        ai_provider=provider,
    )

    assert result == "The images are different."
    assert len(provider.chat_calls) == 1

    call = provider.chat_calls[0]

    assert call["model"] == VISION_MODEL
    assert call["messages"][0]["images"] == [
        str(image1),
        str(image2),
    ]
