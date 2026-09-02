from __future__ import annotations

import base64
import io
import json
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

CLASS_COUNT = 15
CLASS_NAMES = [f"Style-{index}" for index in range(CLASS_COUNT)]


@pytest.fixture
def fake_image() -> Image.Image:
    """Small noisy RGB image, in memory."""
    pixels = np.random.default_rng(7).integers(0, 256, (48, 64, 3), dtype=np.uint8)
    return Image.fromarray(pixels, mode="RGB")


@pytest.fixture
def b64_image(fake_image: Image.Image) -> str:
    buffer = io.BytesIO()
    fake_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def b64_data_url(b64_image: str) -> str:
    return f"data:image/png;base64,{b64_image}"


class FakeOutput:
    def __init__(self, width: int) -> None:
        self.shape = [1, width]
        self.name = "logits"


class FakeSession:
    """Stand-in for the ONNX session, with fixed logits."""

    def __init__(self, width: int = CLASS_COUNT) -> None:
        self.width = width
        self.calls: list[dict[str, Any]] = []

    def get_outputs(self) -> list[FakeOutput]:
        return [FakeOutput(self.width)]

    def run(self, output_names: list[str], feed: dict[str, Any]) -> list[np.ndarray]:
        self.calls.append(feed)
        logits = np.linspace(0.0, 1.0, self.width, dtype=np.float32)
        return [logits[np.newaxis, :]]


@pytest.fixture
def fake_onnx(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    """Install a fake classifier session and restore the globals after."""
    from app.tools import art_style_identifier as identifier

    session = FakeSession()
    monkeypatch.setattr(identifier, "_session", session, raising=False)
    monkeypatch.setattr(identifier, "_classes", list(CLASS_NAMES), raising=False)
    return session


@pytest.fixture
def reset_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear the classifier caches so a test can exercise the loader."""
    from app.tools import art_style_identifier as identifier

    monkeypatch.setattr(identifier, "_session", None, raising=False)
    monkeypatch.setattr(identifier, "_classes", None, raising=False)


@pytest.fixture
def model_artifacts(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Write placeholder artifacts and point the module at them."""
    from app.tools import art_style_identifier as identifier

    def install(class_count: int) -> tuple[Any, Any]:
        model_path = tmp_path / "art_style_identifier.onnx"
        classes_path = tmp_path / "styles_classes.json"
        model_path.write_bytes(b"not-a-real-onnx")
        classes_path.write_text(json.dumps(CLASS_NAMES[:class_count]))
        monkeypatch.setattr(identifier, "ART_STYLE_MODEL_PATH", model_path)
        monkeypatch.setattr(identifier, "ART_STYLE_CLASSES_PATH", classes_path)
        return model_path, classes_path

    return install


@pytest.fixture(autouse=True)
def clear_sessions() -> Any:
    """Empty the in-process chat history around every test."""
    from app import main

    main._SESSIONS.clear()
    yield
    main._SESSIONS.clear()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    """TestClient with config verification stubbed, so no .env is needed."""
    from app import main

    monkeypatch.setattr(main, "verify_config", lambda: [])
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def reset_vlm_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tools import vlm_describe

    monkeypatch.setattr(vlm_describe, "_client", None, raising=False)


@pytest.fixture
def reset_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tools import rag_retriever

    monkeypatch.setattr(rag_retriever, "_model", None, raising=False)
    monkeypatch.setattr(rag_retriever, "_collection", None, raising=False)
