from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import orchestrator
from app.agent.readings import Reading
from tests.conftest import CLASS_NAMES

TOOL_NAMES = {
    "describe_artwork_tool",
    "identify_art_style_tool",
    "generate_artwork_tool",
    "search_met_artworks_tool",
    "search_louvre_artworks_tool",
    "search_british_museum_artworks_tool",
    "search_cleveland_artworks_tool",
    "search_local_gallery_tool",
    "query_art_history_tool",
    "get_art_advice_tool",
}


@pytest.fixture
def captured_tools(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Build an agent without touching Anthropic, and keep its tools.

    The system prompt the agent was built with is kept under the
    ``"__system_prompt__"`` key, so a test can check what Melkov was told.
    """
    captured: dict[str, Any] = {}

    monkeypatch.setattr(orchestrator, "ChatAnthropic", lambda **kwargs: object())

    def fake_create_agent(model: Any, tools: list[Any], system_prompt: str) -> Any:
        captured.update({tool.name: tool for tool in tools})
        captured["__system_prompt__"] = system_prompt
        return object()

    monkeypatch.setattr(orchestrator, "create_agent", fake_create_agent)
    return captured


def test_all_ten_tools_are_registered_and_guard_a_missing_image(
    captured_tools: dict[str, Any]
) -> None:
    _, artifacts = orchestrator.build_melkov_agent(reading=None)
    assert set(captured_tools) - {"__system_prompt__"} == TOOL_NAMES
    assert "ATTACHMENT" not in captured_tools["__system_prompt__"]
    assert set(artifacts) == {
        "generated_image_b64",
        "met_results",
        "louvre_results",
        "british_museum_results",
        "cleveland_results",
        "art_advice",
        "gallery_results",
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
                   "search_met_artworks", "query_art_history", "louvre_search",
                   "british_museum_search", "cleveland_search", "get_art_advice"):
        monkeypatch.setattr(orchestrator, target, blow_up)

    orchestrator.build_melkov_agent(reading=Reading(image_hash="h", image_b64=b64_image))

    assert "TOOL FAILURE" in captured_tools["describe_artwork_tool"].invoke({})
    assert "TOOL FAILURE" in captured_tools["identify_art_style_tool"].invoke({})
    assert "TOOL FAILURE" in captured_tools["generate_artwork_tool"].invoke({"prompt": "x"})
    assert "TOOL FAILURE" in captured_tools["search_met_artworks_tool"].invoke({"query": "x"})
    assert "TOOL FAILURE" in captured_tools["query_art_history_tool"].invoke({"question": "x"})
    assert "TOOL FAILURE" in captured_tools["search_louvre_artworks_tool"].invoke({"query": "x"})
    assert "TOOL FAILURE" in captured_tools["search_british_museum_artworks_tool"].invoke({"query": "x"})
    assert "TOOL FAILURE" in captured_tools["search_cleveland_artworks_tool"].invoke({"query": "x"})
    assert "TOOL FAILURE" in captured_tools["get_art_advice_tool"].invoke({"query": "x"})


def test_museum_and_advice_tools_fill_artifacts_and_summarise(
    captured_tools: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    work = {"title": "Liberty Leading the People", "artist": "Delacroix",
            "date": "1830-01-01T00:00:00Z", "object_url": "https://w.wiki/x"}
    monkeypatch.setattr(orchestrator, "louvre_search",
                        lambda q: {"source": "louvre", "query": q, "results": [work]})
    monkeypatch.setattr(orchestrator, "british_museum_search",
                        lambda q: {"source": "british_museum", "query": q, "results": [],
                                   "error": "timed out."})
    video = {"title": "Skin tones", "channel": "Proko", "url": "https://youtu.be/1",
             "description_snippet": ""}
    monkeypatch.setattr(orchestrator, "get_art_advice", lambda q: [video])

    _, artifacts = orchestrator.build_melkov_agent()
    louvre = captured_tools["search_louvre_artworks_tool"].invoke({"query": "Delacroix"})
    british = captured_tools["search_british_museum_artworks_tool"].invoke({"query": "x"})
    advice = captured_tools["get_art_advice_tool"].invoke({"query": "skin"})

    assert "Found 1 works" in louvre and "Delacroix, 1830" in louvre
    assert artifacts["louvre_results"] == [work]
    assert "TOOL FAILURE" in british and artifacts["british_museum_results"] == []
    assert "Proko" in advice and artifacts["art_advice"] == [video]


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

    reading = Reading(image_hash="h", image_b64=b64_image)
    _, artifacts = orchestrator.build_melkov_agent(reading=reading)

    captured_tools["describe_artwork_tool"].invoke({})
    captured_tools["identify_art_style_tool"].invoke({})
    captured_tools["generate_artwork_tool"].invoke({"prompt": "a harbour"})
    captured_tools["search_met_artworks_tool"].invoke({"query": "Bruegel"})

    assert artifacts["vlm_description"] == "A harbour."
    assert artifacts["style_analysis"] == identification
    assert artifacts["generated_image_b64"]
    assert artifacts["met_results"][0]["title"] == "The Harvesters"
    # What the tools produced is written back to the reading for later turns.
    assert reading.description == "A harbour."
    assert reading.style == identification


def test_cached_reading_is_inlined_and_short_circuits_the_image_tools(
    captured_tools: dict[str, Any], monkeypatch: pytest.MonkeyPatch, b64_image: str
) -> None:
    calls: list[str] = []

    def blow_up(*args: Any, **kwargs: Any) -> Any:
        calls.append("called")
        raise AssertionError("the cache should have answered")

    monkeypatch.setattr(orchestrator, "describe_artwork", blow_up)
    monkeypatch.setattr(orchestrator, "identify_art_style", blow_up)

    identification = {
        "model": "melkov-art-style-cnn",
        "predictions": [{"label": "Baroque", "probability": 0.77}],
        "top_k": 1,
    }
    reading = Reading(
        image_hash="h", image_b64=b64_image, description="A harbour.", style=identification
    )
    _, artifacts = orchestrator.build_melkov_agent(reading=reading)

    prompt = captured_tools["__system_prompt__"]
    assert "ATTACHMENT" in prompt and "A harbour." in prompt and "Baroque 77%" in prompt
    assert "You have not looked at it yet" not in prompt

    assert captured_tools["describe_artwork_tool"].invoke({}) == "A harbour."
    assert "Baroque 77%" in captured_tools["identify_art_style_tool"].invoke({})
    assert calls == []
    assert artifacts["vlm_description"] == "A harbour."
    assert artifacts["style_analysis"] == identification


def test_refused_generation_asks_for_a_rephrase_not_a_retry(
    captured_tools: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(prompt: str) -> Any:
        raise orchestrator.FluxRefusedError("CONTENT_FILTERED")

    monkeypatch.setattr(orchestrator, "generate_artwork", refuse)
    _, artifacts = orchestrator.build_melkov_agent()

    notice = captured_tools["generate_artwork_tool"].invoke({"prompt": "a nude"})

    assert "GENERATION REFUSED (CONTENT_FILTERED)" in notice
    assert "rephrase" in notice
    assert "TOOL FAILURE" not in notice
    assert artifacts["generated_image_b64"] is None


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


def test_local_gallery_tool_passes_full_style_and_fills_artifact(
    monkeypatch: pytest.MonkeyPatch, captured_tools: dict[str, Any]
) -> None:
    work = {"id": "Post_00001", "artist": "Unknown Artist", "style": "Post-Impressionism",
            "caption": "A sunlit wheat field.", "width": 896, "height": 896,
            "s3_key": "images/Post/Post_00001.jpg"}
    seen: list[str] = []

    def fake_style(label: str) -> dict[str, Any]:
        seen.append(label)
        return {"source": "local_gallery", "query_type": "style", "query": label, "results": [work]}

    monkeypatch.setattr(orchestrator, "search_by_style", fake_style)
    _, artifacts = orchestrator.build_melkov_agent(reading=None)

    reply = captured_tools["search_local_gallery_tool"].invoke({"query": "post-impressionism"})

    assert seen == ["post-impressionism"]
    assert "Found 1 works" in reply
    assert artifacts["gallery_results"] == [work]


def test_gallery_resolves_broad_and_aliased_styles() -> None:
    from app.tools.local_gallery_search import resolve_styles

    known = ["Early Renaissance", "High Renaissance", "Northern Renaissance",
             "Post-Impressionism", "Pointillism", "Baroque"]

    assert resolve_styles("renaissance", known) == [
        "Early Renaissance", "High Renaissance", "Northern Renaissance"]
    assert resolve_styles("Post Impressionism", known) == ["Pointillism", "Post-Impressionism"]
    assert resolve_styles("BAROQUE", known) == ["Baroque"]
    assert resolve_styles("Surrealism", known) == []


def test_cleveland_tool_keeps_free_text_dates(
    captured_tools: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    work = {"title": "Water Lilies", "artist": "Claude Monet", "date": "c. 1915-26",
            "object_url": "https://clevelandart.org/art/1960.81"}
    monkeypatch.setattr(orchestrator, "cleveland_search",
                        lambda q: {"source": "cleveland", "query": q, "results": [work]})

    _, artifacts = orchestrator.build_melkov_agent()
    reply = captured_tools["search_cleveland_artworks_tool"].invoke({"query": "Monet"})

    assert "Found 1 works" in reply and "Claude Monet, c. 1915-26" in reply
    assert artifacts["cleveland_results"] == [work]
