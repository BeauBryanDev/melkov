
from __future__ import annotations

import logging
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agent.orchestrator import build_melkov_agent, extract_reply, extract_tool_calls
from app.config import (
    CORS_ORIGINS,
    MAX_HISTORY_MESSAGES,
    MAX_IMAGE_B64_CHARS,
    MAX_SESSIONS,
    verify_config,
)
from app.routers.health import router as health_router
from app.routers.style import router as style_router
from app.tools.art_style_identifier import StyleIdentification, identify_art_style
from app.utils.image_utils import base64_to_pil
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallLog
"""
FastAPI application serving the Melkov art agent.

Exposes ``GET /health`` and ``POST /chat``. Chat history lives in an
in-process dict keyed by ``session_id``: it dies with the process, and it is
bounded on both axes (number of sessions, messages per session) so a long-
running server neither leaks memory nor overflows the model's context window.
Swap ``_SESSIONS`` for Redis when this needs to survive a restart or run on
more than one worker.
"""
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("melkov")

@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Validate configuration on boot, so a missing key fails here."""
    for warning in verify_config():
        
        logger.warning(warning)
        
    logger.info("Melkov ready.")
    yield


app = FastAPI(title="Melkov — Art Agent API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounts POST /style/identify: the CNN answers without an LLM turn, so the
# confidence panel can score an upload the moment it lands.
app.include_router(style_router)

# Mounts GET /health.
app.include_router(health_router)

# Ordered so the least recently used session is the one evicted at capacity.
_SESSIONS: OrderedDict[str, list[BaseMessage]] = OrderedDict()


def _get_history(session_id: str) -> list[BaseMessage]:
    """Return a session's history, evicting the oldest session at capacity.

    Args:
        session_id: The client-supplied conversation id.

    Returns:
        The mutable message list for that session.
    """
    if session_id in _SESSIONS:
        _SESSIONS.move_to_end(session_id)
        
    else:
        _SESSIONS[session_id] = []
        
        while len(_SESSIONS) > MAX_SESSIONS:
            # OrderedDict.popitem() returns the last item, so the evicted
            evicted, _ = _SESSIONS.popitem(last=False)
            logger.info("Evicted session %s at capacity.", evicted)
            
    return _SESSIONS[session_id]


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one conversational turn.

    Args:
        request: The user's message, session id, and optional image.

    Returns:
        Melkov's reply plus any artifacts the tools produced.

    Raises:
        HTTPException: 413 if the attached image is too large, 502 if the
            turn fails outright.
    """
    if request.image_base64 and len(request.image_base64) > MAX_IMAGE_B64_CHARS:
        
        raise HTTPException(
            status_code=413,
            detail="Attached image is too large; please send a smaller one.",
        )

    history = _get_history(request.session_id)
    agent, artifacts = build_melkov_agent(current_image_b64=request.image_base64)

    try:
        result = agent.invoke(
            {"messages": [*history, HumanMessage(content=request.message)]}
        )
    except Exception as error:  # noqa: BLE001
        # The detail is logged, never returned: exception text from the model
        # provider can carry request URLs and key fragments.
        logger.exception("Turn failed for session %s", request.session_id)
        
        raise HTTPException(
            status_code=502,
            detail=f"Melkov could not complete that turn ({type(error).__name__}).",
        ) from error

    messages: list[BaseMessage] = result["messages"]
    reply = extract_reply(messages)

    # Only the user/assistant text is retained. Tool call and result messages
    # are dropped: they are large, and replaying them would invite the model
    # to treat stale tool output as current.
    history.append(HumanMessage(content=request.message))
    history.append(AIMessage(content=reply))
    del history[:-MAX_HISTORY_MESSAGES]

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        tools_used=[
            ToolCallLog(tool=name, input_summary=summary)
            for name, summary in extract_tool_calls(messages)
        ],
        generated_image_base64=artifacts["generated_image_b64"],
        met_results=artifacts["met_results"],
        style_analysis=artifacts["style_analysis"]
        or _classify_or_none(request.image_base64),
        vlm_description=artifacts["vlm_description"],
    )


def _classify_or_none(image_b64: str | None) -> StyleIdentification | None:
    """Score an attached image even when the agent declined to call the tool.

    The prompt asks Melkov to always classify an attachment, but a prompt
    instruction is a request the model can decline — and the confidence panel
    would then sit empty. This backstop is a local CPU pass with no API call,
    and every failure is swallowed: it must never turn a good turn into a 502.

    Args:
        image_b64: This turn's attached image, if any.

    Returns:
        The classifier's answer, or ``None`` if there was no image or it failed.
    """
    if not image_b64:
        
        return None
    
    try:
        return identify_art_style(base64_to_pil(image_b64))
    
    except Exception:  # noqa: BLE001 - the panel degrades, the turn does not
        logger.exception("Backstop classification failed")
        return None


@app.delete("/session/{session_id}")
def clear_session(session_id: str) -> dict[str, str]:
    """Forget one conversation.

    Args:
        session_id: The conversation to drop.

    Returns:
        Whether a session was actually removed.
    """
    existed = _SESSIONS.pop(session_id, None) is not None
    
    return {"status": "cleared" if existed else "not found", "session_id": session_id}
