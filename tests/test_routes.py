from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from app import main
from app.config import MAX_IMAGE_B64_CHARS
from tests.conftest import FakeSession


class FakeAgent:
    """Returns a canned message list, or raises."""

    def __init__(self, reply: str = "A Baroque interior.", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error

    def invoke(self, state: dict[str, Any]) -> dict[str, list[BaseMessage]]:
        if self.error is not None:
            raise self.error
        return {"messages": [AIMessage(content=self.reply)]}


def _patch_agent(monkeypatch: pytest.MonkeyPatch, agent: FakeAgent, artifacts: dict[str, Any]) -> None:
    monkeypatch.setattr(main, "build_melkov_agent", lambda current_image_b64=None: (agent, artifacts))


def _empty_artifacts() -> dict[str, Any]:
    return {
        "generated_image_b64": None,
        "met_results": None,
        "style_analysis": None,
        "vlm_description": None,
    }


def test_health_and_session_lifecycle(client: Any) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "melkov"
    assert body["active_sessions"] == 0

    main._SESSIONS["s1"] = []
    assert client.get("/health").json()["active_sessions"] == 1

    assert client.delete("/session/s1").json()["status"] == "cleared"
    # Idempotent: an unknown id is reported, never a 404.
    second = client.delete("/session/s1")
    assert second.status_code == 200
    assert second.json()["status"] == "not found"


def test_style_identify_status_codes(
    client: Any, monkeypatch: pytest.MonkeyPatch, b64_image: str, fake_onnx: FakeSession
) -> None:
    ok = client.post("/style/identify", json={"image_base64": b64_image, "top_k": 3})
    assert ok.status_code == 200
    assert len(ok.json()["predictions"]) == 3

    bad = client.post("/style/identify", json={"image_base64": "!!!junk!!!"})
    assert bad.status_code == 400

    oversized = client.post(
        "/style/identify", json={"image_base64": "a" * (MAX_IMAGE_B64_CHARS + 1)}
    )
    assert oversized.status_code == 413

    def missing_artifacts(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("no model on disk")

    monkeypatch.setattr("app.routers.style.identify_art_style", missing_artifacts)
    unavailable = client.post("/style/identify", json={"image_base64": b64_image})
    assert unavailable.status_code == 503


def test_chat_carries_artifacts_and_fails_safely(
    client: Any, monkeypatch: pytest.MonkeyPatch, b64_image: str, fake_onnx: FakeSession
) -> None:
    artifacts = _empty_artifacts()
    artifacts["vlm_description"] = "A harbour at dusk."
    _patch_agent(monkeypatch, FakeAgent(), artifacts)

    body = client.post("/chat", json={"message": "what is this?", "session_id": "s1"}).json()
    assert body["reply"] == "A Baroque interior."
    assert body["session_id"] == "s1"
    assert body["vlm_description"] == "A harbour at dusk."

    # The agent left style_analysis empty, so the local backstop fills it.
    backstopped = client.post(
        "/chat", json={"message": "and this?", "session_id": "s1", "image_base64": b64_image}
    ).json()
    assert backstopped["style_analysis"]["model"] == "melkov-art-style-cnn"

    oversized = client.post(
        "/chat",
        json={"message": "x", "session_id": "s1", "image_base64": "a" * (MAX_IMAGE_B64_CHARS + 1)},
    )
    assert oversized.status_code == 413

    _patch_agent(monkeypatch, FakeAgent(error=RuntimeError("sk-ant-secret leaked here")), _empty_artifacts())
    failed = client.post("/chat", json={"message": "x", "session_id": "s1"})
    assert failed.status_code == 502
    assert "sk-ant-secret" not in failed.json()["detail"]
