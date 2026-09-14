"""``POST /artwork/read``: the upload-time read that fills the readings cache.

Offline like the rest of the suite: the VLM is a patched function on the
router module, the classifier is the fake ONNX session.
"""

from __future__ import annotations

from typing import Any

import pytest

from app import main
from app.agent import readings
from app.config import MAX_IMAGE_B64_CHARS
from app.routers import artwork as artwork_router
from tests.conftest import FakeSession
from tests.test_routes import FakeAgent, _empty_artifacts


def test_read_fills_cache_once_and_chat_reuses_it(
    client: Any, monkeypatch: pytest.MonkeyPatch, b64_image: str, fake_onnx: FakeSession
) -> None:
    calls: list[Any] = []

    def fake_describe(image: Any, instruction: str | None = None) -> str:
        calls.append(image)
        return "A harbour at dusk."

    monkeypatch.setattr(artwork_router, "describe_artwork", fake_describe)

    first = client.post("/artwork/read", json={"session_id": "s1", "image_base64": b64_image})
    assert first.status_code == 200
    body = first.json()
    assert body["vlm_description"] == "A harbour at dusk."
    assert body["style_analysis"]["model"] == "melkov-art-style-cnn"
    assert body["cached"] is False

    # Same image again, from another session: served from the cache, no model run.
    again = client.post("/artwork/read", json={"session_id": "s2", "image_base64": b64_image}).json()
    assert again["cached"] is True
    assert len(calls) == 1
    assert len(fake_onnx.calls) == 1

    # A chat turn with no bytes now sees the primed reading.
    seen: list[Any] = []

    def capture(reading: Any = None) -> Any:
        seen.append(reading)
        return FakeAgent(), _empty_artifacts()

    monkeypatch.setattr(main, "build_melkov_agent", capture)
    turn = client.post("/chat", json={"message": "what is this?", "session_id": "s1"}).json()
    assert seen[0] is readings.current("s1")
    assert seen[0].description == "A harbour at dusk."
    # The backstop serves the cached scores rather than classifying again.
    assert turn["style_analysis"]["model"] == "melkov-art-style-cnn"
    assert len(fake_onnx.calls) == 1


def test_read_status_codes(
    client: Any, monkeypatch: pytest.MonkeyPatch, b64_image: str, fake_onnx: FakeSession
) -> None:
    oversized = client.post(
        "/artwork/read", json={"session_id": "s1", "image_base64": "a" * (MAX_IMAGE_B64_CHARS + 1)}
    )
    assert oversized.status_code == 413

    garbage = client.post("/artwork/read", json={"session_id": "s1", "image_base64": "not-base64!!"})
    assert garbage.status_code == 400

    def broken(image: Any, instruction: str | None = None) -> str:
        raise RuntimeError("Space asleep")

    monkeypatch.setattr(artwork_router, "describe_artwork", broken)
    failed = client.post("/artwork/read", json={"session_id": "s1", "image_base64": b64_image})
    assert failed.status_code == 502
    assert "RuntimeError" in failed.json()["detail"]
    # The classifier ran before the Space failed, so its scores are kept for /chat's backstop.
    assert readings.current("s1").style is not None
    assert readings.current("s1").description is None
