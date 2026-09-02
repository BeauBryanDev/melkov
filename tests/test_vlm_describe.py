from __future__ import annotations

import os
from typing import Any

import pytest
from PIL import Image

from app.tools import vlm_describe


class FakeGradioClient:
    """Records the payload and can be told to fail."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.paths: list[str] = []
        self.payloads: list[dict[str, Any]] = []
        self.sizes: list[tuple[int, int]] = []

    def predict(self, payload: dict[str, Any], api_name: str = "") -> str:
        self.payloads.append(payload)
        path = payload["files"][0]["path"]
        self.paths.append(path)
        # Read it here: the finally block deletes it before predict returns.
        with Image.open(path) as uploaded:
            self.sizes.append(uploaded.size)
        if self.error is not None:
            raise self.error
        return "  A luminous harbour scene.  "


def test_coerce_description_reads_every_returned_shape() -> None:
    assert vlm_describe._coerce_description("a reply") == "a reply"
    assert vlm_describe._coerce_description(("a reply", None)) == "a reply"
    assert vlm_describe._coerce_description(["a reply"]) == "a reply"
    for key in ("description", "text", "output", "caption"):
        assert vlm_describe._coerce_description({key: " a reply "}) == "a reply"


def test_coerce_description_rejects_unusable_payloads() -> None:
    with pytest.raises(RuntimeError, match="no text field"):
        vlm_describe._coerce_description({"unexpected": "a reply"})

    with pytest.raises(RuntimeError, match="unusable response"):
        vlm_describe._coerce_description(None)


def test_describe_artwork_downscales_and_always_cleans_up(
    monkeypatch: pytest.MonkeyPatch, reset_vlm_client: None
) -> None:
    large = Image.new("RGB", (2000, 1000), (10, 20, 30))

    client = FakeGradioClient()
    monkeypatch.setattr(vlm_describe, "_get_client", lambda: client)

    assert vlm_describe.describe_artwork(large) == "A luminous harbour scene."
    assert max(client.sizes[0]) == vlm_describe.MAX_UPLOAD_DIM
    assert not os.path.exists(client.paths[0])

    # The temp PNG leaked into /tmp before the finally block existed.
    failing = FakeGradioClient(error=RuntimeError("space is asleep"))
    monkeypatch.setattr(vlm_describe, "_get_client", lambda: failing)
    with pytest.raises(RuntimeError, match="space is asleep"):
        vlm_describe.describe_artwork(large)
    assert not os.path.exists(failing.paths[0])
