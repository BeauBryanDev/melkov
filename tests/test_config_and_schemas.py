from __future__ import annotations

import pytest
from pydantic import ValidationError

from app import config
from app.schemas.chat import ChatRequest, ChatResponse, StyleIdentification
from app.schemas.style import StyleRequest
from app.tools.art_style_identifier import MODEL_NAME


def test_verify_config_raises_only_on_the_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # The constants are Final and read at import, so patch them, not the env.
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        config.verify_config()

    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(config, "NVIDIA_API_KEY", "")
    warnings = config.verify_config()
    assert any("NVIDIA_API_KEY" in warning for warning in warnings)


def test_chat_request_validation() -> None:
    request = ChatRequest(message="hello", session_id="s1")
    assert request.image_base64 is None

    with pytest.raises(ValidationError):
        ChatRequest(message="hello", session_id="")

    with pytest.raises(ValidationError):
        ChatRequest(message="", session_id="s1")


def test_style_request_top_k_bounds() -> None:
    assert StyleRequest(image_base64="abc").top_k >= 1

    with pytest.raises(ValidationError):
        StyleRequest(image_base64="abc", top_k=0)

    with pytest.raises(ValidationError):
        StyleRequest(image_base64="abc", top_k=16)


def test_wire_contract_between_tool_and_schema() -> None:
    # The tool's TypedDict must validate straight into the response schema.
    tool_output = {
        "model": MODEL_NAME,
        "predictions": [{"label": "Baroque", "probability": 0.77}],
        "top_k": 1,
    }
    parsed = StyleIdentification.model_validate(tool_output)
    assert parsed.predictions[0].label == "Baroque"

    response = ChatResponse(reply="hi", session_id="s1")
    assert response.style_analysis is None
    assert response.vlm_description is None
    assert response.met_results is None
    assert response.generated_image_base64 is None
