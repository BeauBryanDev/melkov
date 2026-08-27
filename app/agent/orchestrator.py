
from __future__ import annotations

import logging
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import tool

from app.agent.prompts import MELKOV_SYSTEM_PROMPT
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, LLM_TEMPERATURE
from app.tools.flux_generate import generate_artwork
from app.tools.met_search import search_met_artworks
from app.tools.art_style_identifier import StyleIdentification, identify_art_style
from app.tools.rag_retriever import query_art_history
from app.tools.vlm_describe import describe_artwork
from app.utils.image_utils import base64_to_pil, pil_to_base64

logger = logging.getLogger(__name__)


class Artifacts(TypedDict):
    """Side-channel for tool output the model cannot carry in text."""

    generated_image_b64: str | None
    met_results: list[dict[str, Any]] | None
    style_analysis: StyleIdentification | None
    vlm_description: str | None


def build_melkov_agent(current_image_b64: str | None = None) -> tuple[Any, Artifacts]:
    """
    Build a Melkov agent bound to this turn's uploaded image.

    A fresh agent is built per turn because the image is captured by closure.
    The construction itself is cheap — the expensive resources (embedding
    model, Chroma collection, Gradio client) are process-wide singletons
    inside the tool modules, not rebuilt here.

    Args:
        current_image_b64: The image uploaded with this turn, if any.

    Returns:
        A ``(agent, artifacts)`` pair. Invoke the agent with
        ``{"messages": [...]}``; read ``artifacts`` afterwards.
    """
    artifacts: Artifacts = {
        "generated_image_b64": None,
        "met_results": None,
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
        if not current_image_b64:
            return (
                "No image was attached to this message. Ask the user to upload "
                "one before analysing it."
            )
        try:
            description = describe_artwork(base64_to_pil(current_image_b64))
        
        except Exception as error:  # noqa: BLE001 - reported to the model, not raised
            logger.exception("vlm_describe failed")
            
            return _tool_error("the vision model", error)

        # Kept in the side-channel as well as returned: the frontend shows the
        # VLM's own words verbatim, not Melkov's paraphrase of them.
        artifacts["vlm_description"] = description

        return description

    @tool
    def generate_artwork_tool(prompt: str) -> str:
        """
        Create a brand-new image from a text description.

        Use for requests to generate, paint, imagine or visualise something
        that does not exist yet. Write a rich, concrete visual prompt —
        subject, composition, medium, palette, lighting, style. The image is
        returned to the user automatically as an attachment, so describe your
        intent in the reply rather than pretending to show it.

        Keep the prompt under 700 characters: the generator hard-rejects
        anything longer, and over-length prompts are trimmed before sending.

        Args:
            prompt: A detailed visual description, under 700 characters.
        """
        try:
            image = generate_artwork(prompt)
            
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
        if not current_image_b64:
            return (
                "No image was attached to this message. Ask the user to upload "
                "one before classifying its style."
            )
        try:
            result = identify_art_style(base64_to_pil(current_image_b64))

        except Exception as error:  # noqa: BLE001
            logger.exception("art_style_identifier failed")

            return _tool_error("the style classifier", error)

        artifacts["style_analysis"] = result

        ranked = ", ".join(
            f"{item['label']} {item['probability']:.0%}"
            for item in result["predictions"]
        )
        
        return f"Style classifier ({result['model']}) ranks this work: {ranked}."


    # Melkov tools are all functions, not classes, so they can't be decorated.
    tools: list[Any] = [
        describe_artwork_tool,
        identify_art_style_tool,
        generate_artwork_tool,
        search_met_artworks_tool,
        query_art_history_tool,
    ]

    # temperature is passed only when configured: Sonnet 5 and later reject
    # the argument with a 400 rather than ignoring it.
    model_kwargs: dict[str, Any] = {
        "model": ANTHROPIC_MODEL,
        "api_key": ANTHROPIC_API_KEY,
    }
    if LLM_TEMPERATURE is not None:
        model_kwargs["temperature"] = LLM_TEMPERATURE
    model = ChatAnthropic(**model_kwargs)

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=MELKOV_SYSTEM_PROMPT,
    )
    return agent, artifacts


def _tool_error(subject: str, error: Exception) -> str:
    """Phrase a tool failure as something the model can recover from.

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
    """List the tools the agent used, in call order.

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
