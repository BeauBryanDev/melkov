from __future__ import annotations

import pytest

from app.agent import readings


def test_same_image_shares_one_reading_and_prefix_is_ignored() -> None:
    first = readings.remember("s1", "data:image/png;base64,aGVsbG8=")
    second = readings.remember("s2", "aGVsbG8=")

    assert first is second
    assert first.image_b64 == "aGVsbG8="
    assert readings.current("s1") is readings.current("s2") is first


def test_new_upload_replaces_the_session_artwork_and_forget_is_per_session() -> None:
    old = readings.remember("s1", "aGVsbG8=")
    new = readings.remember("s1", "d29ybGQ=")

    assert readings.current("s1") is new and new is not old

    readings.forget_session("s1")
    assert readings.current("s1") is None
    # Idempotent, and never a KeyError for an unknown session.
    readings.forget_session("s1")
    assert readings.current("never") is None


def test_cache_is_bounded_lru_and_a_dangling_session_is_cleaned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(readings, "MAX_READINGS", 2)

    readings.remember("a", "AAAA")
    readings.remember("b", "BBBB")
    readings.current("a")  # touch: "a" is now the most recent
    readings.remember("c", "CCCC")  # evicts "b"

    assert readings.current("a") is not None
    assert readings.current("c") is not None
    assert readings.current("b") is None
    assert "b" not in readings._SESSION_IMAGE
