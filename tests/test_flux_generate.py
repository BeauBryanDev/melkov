from __future__ import annotations

import json

import pytest
import responses

from app.tools import flux_generate


def test_fit_prompt_trims_only_over_length_prompts() -> None:
    assert flux_generate._fit_prompt("  a quiet harbour at dawn  ") == (
        "a quiet harbour at dawn"
    )

    prompt = ("a gilded baroque interior with warm candlelight. " * 30).strip()
    fitted = flux_generate._fit_prompt(prompt)
    assert len(fitted) <= flux_generate.MAX_PROMPT_CHARS
    assert fitted in prompt
    assert fitted.endswith("candlelight")


def test_find_image_walks_the_envelope() -> None:
    payload = "x" * 300
    for key in flux_generate._IMAGE_KEYS:
        assert flux_generate._find_image({"artifacts": [{key: payload}]}) == payload

    # Short strings are formats or URLs, not payloads.
    assert flux_generate._find_image({"image": "png"}) is None
    assert flux_generate._find_image({"status": "ok", "artifacts": []}) is None
    assert flux_generate._find_image({"a": {"b": {"c": {"d": {"e": {"image": payload}}}}}}) is None


def test_generate_artwork_needs_a_key_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(flux_generate, "NVIDIA_API_KEY", "")
    with responses.RequestsMock() as mock:
        with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
            flux_generate.generate_artwork("a still life")
        assert not mock.calls


@responses.activate
def test_image_key_is_absent_for_text_to_image(
    monkeypatch: pytest.MonkeyPatch, b64_image: str
) -> None:
    monkeypatch.setattr(flux_generate, "NVIDIA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        flux_generate.FLUX_INVOKE_URL,
        json={"artifacts": [{"b64_json": b64_image}]},
        status=200,
    )

    flux_generate.generate_artwork("a still life")
    body = json.loads(responses.calls[0].request.body)
    # An empty placeholder is rejected with 422; the key must simply be gone.
    assert "image" not in body

    flux_generate.generate_artwork("a still life", init_image_b64=b64_image)
    body = json.loads(responses.calls[1].request.body)
    assert body["image"] == [b64_image]
