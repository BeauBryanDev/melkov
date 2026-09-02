from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import orchestrator
from tests.conftest import CLASS_NAMES

TOOL_NAMES = {
    "describe_artwork_tool",
    "identify_art_style_tool",
    "generate_artwork_tool",
    "search_met_artworks_tool",
    "query_art_history_tool",
}


@pytest.fixture
def captured_tools(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Build an agent without touching Anthropic, and keep its tools."""
    captured: dict[str, Any] = {}

    monkeypatch.setattr(orchestrator, "ChatAnthropic", lambda **kwargs: object())

    def fake_create_agent(model: Any, tools: list[Any], system_prompt: str) -> Any:
        captured.update({tool.name: tool for tool in tools})
        return object()

    monkeypatch.setattr(orchestrator, "create_agent", fake_create_agent)
    return captured


def test_all_five_tools_are_registered_and_guard_a_missing_image(
    captured_tools: dict[str, Any]
) -> None:
    _, artifacts = orchestrator.build_melkov_agent(current_image_b64=None)
    assert set(captured_tools) == TOOL_NAMES
    assert set(artifacts) == {
        "generated_image_b64",
        "met_results",
        "style_analysis",
        "vlm_description",
    }

    for name in ("describe_artwork_tool", "identify_art_style_tool"):
        assert "No image was attached" in captured_tools[name].invoke({})


def test_tools_report_failures_instead_of_raising(
    captured_tools: dict[str, Any], monkeypatch: pytest.MonkeyPatch, b64_image: str
) -> None:
    def blow_up(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("upstream is down")

    for target in ("describe_artwork", "identify_art_style", "generate_artwork",
                   "search_met_artworks", "query_art_history"):
        monkeypatch.setattr(orchestrator, target, blow_up)

    orchestrator.build_melkov_agent(current_image_b64=b64_image)

    assert "TOOL FAILURE" in captured_tools["describe_artwork_tool"].invoke({})
    assert "TOOL FAILURE" in captured_tools["identify_art_style_tool"].invoke({})
    assert "TOOL FAILURE" in captured_tools["generate_artwork_tool"].invoke({"prompt": "x"})
    assert "TOOL FAILURE" in captured_tools["search_met_artworks_tool"].invoke({"query": "x"})
    assert "TOOL FAILURE" in captured_tools["query_art_history_tool"].invoke({"question": "x"})


def test_tools_fill_the_artifacts_side_channel(
    captured_tools: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    b64_image: str,
    fake_image: Any,
) -> None:
    identification = {
        "model": "melkov-art-style-cnn",
        "predictions": [{"label": CLASS_NAMES[0], "probability": 0.8}],
        "top_k": 1,
    }
    monkeypatch.setattr(orchestrator, "describe_artwork", lambda image: "A harbour.")
    monkeypatch.setattr(orchestrator, "identify_art_style", lambda image: identification)
    monkeypatch.setattr(orchestrator, "generate_artwork", lambda prompt: fake_image)
    monkeypatch.setattr(
        orchestrator, "search_met_artworks", lambda query: [{"title": "The Harvesters", "artist": "Bruegel"}]
    )

    _, artifacts = orchestrator.build_melkov_agent(current_image_b64=b64_image)

    captured_tools["describe_artwork_tool"].invoke({})
    captured_tools["identify_art_style_tool"].invoke({})
    captured_tools["generate_artwork_tool"].invoke({"prompt": "a harbour"})
    captured_tools["search_met_artworks_tool"].invoke({"query": "Bruegel"})

    assert artifacts["vlm_description"] == "A harbour."
    assert artifacts["style_analysis"] == identification
    assert artifacts["generated_image_b64"]
    assert artifacts["met_results"][0]["title"] == "The Harvesters"


def test_reply_and_tool_calls_are_read_back_from_the_messages() -> None:
    blocks = [{"type": "text", "text": "A Baroque interior."}]
    messages = [
        HumanMessage(content="what is this?"),
        AIMessage(content="", tool_calls=[
            {"name": "identify_art_style_tool", "args": {}, "id": "1"},
            {"name": "query_art_history_tool", "args": {"question": "q" * 200}, "id": "2"},
        ]),
        AIMessage(content=blocks),
    ]

    assert orchestrator.extract_reply(messages) == "A Baroque interior."

    calls = orchestrator.extract_tool_calls(messages)
    assert [name for name, _ in calls] == [
        "identify_art_style_tool",
        "query_art_history_tool",
    ]
    assert len(calls[1][1]) <= 120

    fallback = orchestrator.extract_reply([HumanMessage(content="hi")])
    assert "could not put a reply together" in fallback
