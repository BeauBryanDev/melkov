from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.tools import art_style_identifier as identifier
from tests.conftest import CLASS_COUNT, FakeSession


def test_preprocessing_letterboxes_and_matches_the_trained_tensor(
    fake_image: Image.Image,
) -> None:
    image = Image.new("RGB", (64, 48), (200, 30, 30))
    padded = identifier._pad_to_square(image)
    assert padded.size == (64, 64)
    # Original pixels sit centred, padding stays black.
    assert padded.getpixel((32, 32)) == (200, 30, 30)
    assert padded.getpixel((32, 1)) == (0, 0, 0)

    tensor = identifier._preprocess(fake_image)
    assert tensor.shape == (1, 3, identifier.IMAGE_SIZE, identifier.IMAGE_SIZE)
    assert tensor.dtype == np.float32


def test_softmax_is_normalised_and_stable() -> None:
    probabilities = identifier._softmax(np.array([[1000.0, 1001.0, 999.0]]))
    assert np.isfinite(probabilities).all()
    assert probabilities.sum() == pytest.approx(1.0)


def test_identify_art_style_ranks_and_clamps(
    fake_onnx: FakeSession, fake_image: Image.Image
) -> None:
    result = identifier.identify_art_style(fake_image, top_k=3)
    probabilities = [item["probability"] for item in result["predictions"]]
    assert len(result["predictions"]) == 3
    assert probabilities == sorted(probabilities, reverse=True)
    assert result["model"] == identifier.MODEL_NAME

    clamped = identifier.identify_art_style(fake_image, top_k=99)
    assert clamped["top_k"] == CLASS_COUNT


def test_load_resources_guards_missing_and_mismatched_artifacts(
    reset_identifier: None,
    model_artifacts: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
) -> None:
    monkeypatch.setattr(
        identifier.ort, "InferenceSession", lambda *args, **kwargs: FakeSession()
    )

    # A stale class list would silently shift every label.
    model_path, classes_path = model_artifacts(3)
    with pytest.raises(ValueError, match="do not match"):
        identifier._load_resources()

    classes_path.unlink()
    with pytest.raises(FileNotFoundError, match="class list"):
        identifier._load_resources()

    model_path.unlink()
    with pytest.raises(FileNotFoundError, match="Style model"):
        identifier._load_resources()
