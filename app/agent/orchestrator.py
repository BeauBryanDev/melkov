
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import tool

from app.agent.prompts import ( MELKOV_SYSTEM_PROMPT, 
                               attachment_prompt, 
                               format_style_ranking )
from app.agent.readings import Reading
from app.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    LLM_EFFORT,
    LLM_MAX_TOKENS,
    LLM_PROMPT_CACHE,
    LLM_TEMPERATURE,
    LLM_THINKING_ENABLED,
)
## All Melkov tools ##
from app.tools.flux_generate import FluxRefusedError, generate_artwork
from app.tools.met_search import search_met_artworks
from app.tools.art_style_identifier import StyleIdentification, identify_art_style
from app.tools.rag_retriever import query_art_history
from app.tools.vlm_describe import describe_artwork
from app.tools.louvre_search import louvre_search
from app.tools.british_museum_search import british_museum_search
from app.tools.artist_advisor import get_art_advice
from app.utils.image_utils import base64_to_pil, pil_to_base64

logger = logging.getLogger(__name__)


class Artifacts(TypedDict):
    """Side-channel for tool output the model cannot carry in text."""

    generated_image_b64: str | None
    met_results: list[dict[str, Any]] | None
    louvre_results: list[dict[str, Any]] | None
    british_museum_results: list[dict[str, Any]] | None
    art_advice: list[dict[str, Any]] | None
    style_analysis: StyleIdentification | None
    vlm_description: str | None


def build_melkov_agent(reading: Reading | None = None) -> tuple[Any, Artifacts]:
    """
    Build a Melkov agent bound to the artwork in this session's frame.

    A fresh agent is built per turn because the image is captured by closure.
    The construction itself is cheap -> the expensive resources (embedding
    model, Chroma collection, Gradio client) are process-wide singletons
    inside the tool modules, not rebuilt here.

    The reading is the cache entry for the artwork, whether it arrived with
    this turn or an earlier one. Whatever the tools have already said about
    it is inlined into the system prompt, so a follow-up question costs no
    tool call; the two image tools fall back to the same cache when the model
    calls them anyway, and write into it when they do real work.
    """
    artifacts: Artifacts = {
        "generated_image_b64": None,
        "met_results": None,
        "louvre_results": None,
        "british_museum_results": None,
        "art_advice": None,
        "style_analysis": None,
        "vlm_description": None,
    }

    @tool
    def describe_artwork_tool() -> str:
        """
        Look at the image the user attached to this message and describe it.

        This is your own trained eye for paintings. Use it whenever the user
        has attached an image and wants it read, analysed, identified or
        discussed. Takes no arguments — the attached image is supplied
        automatically. Do not use it when no image was attached.
        """
        if reading is None:
            return (
                "No image was attached to this message. Ask the user to upload "
                "one before analysing it."
            )
        # Already read on an earlier turn: answer from the cache rather than
        # waking the VLM Space again for an unchanged picture.
        if reading.description is None:
            try:
                reading.description = describe_artwork(base64_to_pil(reading.image_b64))

            except Exception as error:  # noqa: BLE001 - reported to the model, not raised
                logger.exception("vlm_describe failed")

                return _tool_error("the vision model", error)

        # Kept in the side-channel as well as returned: the frontend shows the
        # VLM's own words verbatim, not Melkov's paraphrase of them.
        artifacts["vlm_description"] = reading.description

        return reading.description

    @tool
    def generate_artwork_tool(prompt: str) -> str:
        """
        Create a brand-new image from a text description.

        Use for requests to generate, paint, imagine or visualise something
        that does not exist yet. Write a rich, concrete visual prompt —
        subject, composition, medium, palette, lighting, style. The image is
        returned to the user automatically as an attachment, so describe your
        intent in the reply rather than pretending to show it.

        Args:
            prompt: A detailed visual description, under 700 characters.
        """
        try:
            image = generate_artwork(prompt)

        except FluxRefusedError as refusal:

            logger.info("flux_generate refused the prompt (%s)", refusal.reason)
            
            return (
                f"GENERATION REFUSED ({refusal.reason}): the image generator's "
                "content filter declined this prompt; the service itself is "
                "working. Tell the user plainly that the generator would not "
                "render this subject, then offer to try again with a rephrased "
                "prompt — clothed or draped figures, a different framing, or "
                "an emphasis on setting, palette and technique instead of the "
                "body — and do so at once if they agree."
            )

        except Exception as error:  # noqa: BLE001
            logger.exception("flux_generate failed")
            
            return _tool_error("the image generator", error)

        artifacts["generated_image_b64"] = pil_to_base64(image)
        
        return f"Image generated successfully for the prompt: {prompt!r}."


    @tool
    def search_met_artworks_tool(query: str) -> str:
        """
        Find real artworks in the Metropolitan Museum of Art collection.

        Use whenever the user wants to see, find, browse or compare actual
        works — by artist, style, movement, period, medium or subject. The
        matching works are attached to the reply automatically. Prefer this
        over generating an image when the user asks about real art.

        Args:
            query: What to search for, e.g. "Vermeer" or "Japanese woodblock".
        """
        try:
            results = search_met_artworks(query)
            
        except Exception as error:  # noqa: BLE001
            logger.exception("met_search failed")
            return _tool_error("the MET collection API", error)

        artifacts["met_results"] = results
        
        if not results:
            return f"No works found in the MET collection for {query!r}."

        titles = "; ".join(
            
            f"{item.get('title') or 'Untitled'} "
            f"({item.get('artist') or 'artist unknown'})"
            for item in results
        )
        return f"Found {len(results)} works: {titles}"
    
    
    @tool
    def search_louvre_artworks_tool(query: str) -> str:
        """
        Search the Louvre's collection by title or artist. Use when the person
        asks for the Louvre, or when the MET search came back empty.

        Args:
            query: An artwork title or artist name, e.g. "Delacroix".
        """
        return _run_museum_search(
            "louvre_results", "the Louvre collection (Wikidata)", louvre_search, query
        )

    @tool
    def search_british_museum_artworks_tool(query: str) -> str:
        """
        Search the British Museum's collection by title or artist. Use when the
        person asks for it, or when the MET search came back empty.

        Args:
            query: An object title or artist name, e.g. "Hokusai".
        """
        return _run_museum_search(
            "british_museum_results",
            "the British Museum collection (Wikidata)",
            british_museum_search,
            query,
        )

    def _run_museum_search(
        artifact_key: str, 
        subject: str, 
        search: Any, 
        query: str
    ) -> str:
        
        try:
            envelope = search(query)
            
        except Exception as error:  # noqa: BLE001
            logger.exception("%s failed", artifact_key)
            return _tool_error(subject, error)

        results = envelope.get("results") or []
        artifacts[artifact_key] = results  # type: ignore[literal-required]

        if envelope.get("error"):
            return f"TOOL FAILURE: {envelope['error']} Tell the user and carry on."
        
        if not results:
            return f"No works found in {subject} for {query!r}."

        summary = "; ".join(
            f"{item.get('title') or 'Untitled'} "
            f"({item.get('artist') or 'artist unknown'}, "
            f"{_year_of(item.get('date'))}) {item.get('object_url') or ''}".rstrip()
            for item in results
        )
        return f"Found {len(results)} works: {summary}"

    @tool
    def query_art_history_tool(question: str) -> str:
        """
        Search the art-history library for grounded, citable passages.

        The library holds full texts by Gombrich, Arnheim, Itten, Kandinsky
        and others. Use it for conceptual or historical questions — movements,
        techniques, theory, biography, cultural context — and any time a claim
        should rest on a source rather than memory. Returns passages with
        their book and page, which you may reference naturally in your reply.

        Args:
            question: The art-history question, in natural language.
        """
        try:
            return query_art_history(question)
        
        except Exception as error:  # noqa: BLE001
            logger.exception("rag_retriever failed")
            return _tool_error("the art-history library", error)

    @tool
    def identify_art_style_tool() -> str:
        """
        Score the attached image against the fifteen art-historical styles.

        This is your trained classifier, not a guess: it returns ranked styles
        with confidences. Call it on every attached artwork, alongside your
        own reading of the picture, before naming a movement or period. Takes
        no arguments — the attached image is supplied automatically. Do not
        use it when no image was attached.
        """
        if reading is None:
            return (
                "No image was attached to this message. Ask the user to upload "
                "one before classifying its style."
            )
        if reading.style is None:
            try:
                reading.style = identify_art_style(base64_to_pil(reading.image_b64))

            except Exception as error:  # noqa: BLE001
                logger.exception("art_style_identifier failed")

                return _tool_error("the style classifier", error)

        artifacts["style_analysis"] = reading.style

        return format_style_ranking(reading.style)
    
    
    @tool
    def get_art_advice_tool(query: str) -> str:
        """
        Find painting-technique videos (brushwork, colour mixing, skin tones,
        impasto) from trusted artist channels. Use for "how do I paint" questions.

        Args:
            query: The technique, in English, e.g. "realistic skin tones in oil".
        """
        try:
            results = get_art_advice(query)
            
        except Exception as error:  # noqa: BLE001
            logger.exception("artist_advisor failed")
            return _tool_error("the painting-advice video search", error)

        artifacts["art_advice"] = results
        
        if not results:
            return (
                f"No videos from the trusted channels matched {query!r}. "
                "Suggest a more specific technique, or answer from your own "
                "knowledge of painting."
            )
            
        listing = "; ".join(
            f"{item['title']} by {item['channel']} - {item['url']}" for item in results
        )
        return f"Found {len(results)} videos: {listing}"

    # Melkov tools are all functions, not classes, so they can't be decorated.
    tools: list[Any] = [
        describe_artwork_tool,
        identify_art_style_tool,
        generate_artwork_tool,
        search_met_artworks_tool,
        search_louvre_artworks_tool,
        search_british_museum_artworks_tool,
        query_art_history_tool,
        get_art_advice_tool,
    ]

    # Temperature only when configured - Sonnet 5 rejects it with a 400.
    # Thinking off unless asked: Sonnet 5 thinks by default and bills it as output.
    model_kwargs: dict[str, Any] = {
        
        "model": ANTHROPIC_MODEL,
        "api_key": ANTHROPIC_API_KEY,
        "max_tokens": LLM_MAX_TOKENS,
        # Sonnet 5 rejects budget_tokens; "adaptive" is its only on-mode.
        "thinking": {"type": "adaptive" if LLM_THINKING_ENABLED else "disabled"},
    }
    if LLM_EFFORT:
        model_kwargs["reasoning_effort"] = LLM_EFFORT
        
    if LLM_TEMPERATURE is not None:

        model_kwargs["temperature"] = LLM_TEMPERATURE

    # Prompt caching.`model_kwargs` are spread into the request payload, so
    # this is the API's top-level `cache_control`: a breakpoint on the last
    # cacheable block of each call, i.e. the whole prefix. Nothing about the
    # messages or tools changes; a prefix under the model's minimum cacheable
    # size is simply not cached, with no error.
    if LLM_PROMPT_CACHE:
        model_kwargs["model_kwargs"] = {"cache_control": {"type": "ephemeral"}}
        
    model = ChatAnthropic(**model_kwargs)

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=MELKOV_SYSTEM_PROMPT + attachment_prompt(reading),
    )
    return agent, artifacts

def _year_of(date: str | None) -> str:
    """Year of a Wikidata timestamp like 1503-01-01T00:00:00Z."""
    if not date:
        return "date unknown"
    
    return date.lstrip("-")[:4] if date[0] != "-" else f"{date[1:5]} BC"


def _tool_error(subject: str, error: Exception) -> str:
    """
    Phrase a tool failure as something the model can recover from.

    Returned rather than raised on purpose: an exception escaping a tool ends
    the whole turn with a 500, whereas a plain-language failure lets Melkov
    tell the user what broke and carry on with the skills that still work.

    Args:
        subject: What failed, in words the model can repeat to the user.
        error: The exception that was caught.

    Returns:
        A short failure notice for the model.
    """
    return (
        f"TOOL FAILURE: {subject} is unavailable right now "
        f"({type(error).__name__}). Tell the user plainly that this part did "
        "not work, then help them with what you can do without it."
    )


def extract_reply(messages: list[BaseMessage]) -> str:
    """Pull the user-facing answer out of a finished turn.

    Args:
        messages: The full message list returned by the agent.

    Returns:
        The final assistant text, or a fallback if the turn produced none.
    """
    for message in reversed(messages):
        
        if isinstance(message, AIMessage) and not message.tool_calls:
            
            content = message.content
            
            if isinstance(content, str) and content.strip():
                return content
            # Anthropic returns content as a list of typed blocks when the
            # turn mixes text with tool use.
            if isinstance(content, list):
                
                text = "".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                    
                ).strip()
                
                if text:
                    return text
                
    return "I could not put a reply together for that one — try rephrasing?"


def extract_tool_calls(messages: list[BaseMessage]) -> list[tuple[str, str]]:
    """
    List the tools the agent used, in call order.

    Replaces the ``intermediate_steps`` key of the old ``AgentExecutor``,
    which LangChain 1.x no longer produces.

    Args:
        messages: The full message list returned by the agent.

    Returns:
        ``(tool_name, argument_summary)`` pairs.
    """
    calls: list[tuple[str, str]] = []
    
    for message in messages:
        
        for call in getattr(message, "tool_calls", None) or []:
            
            name = call.get("name", "?")
            args = call.get("args", {})
            
            summary = ", ".join(f"{key}={value!r}" for key, value in args.items())
            
            calls.append((name, summary[:120]))
            
            
    return calls
