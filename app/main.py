
from __future__ import annotations

import logging
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agent import readings
from app.agent.orchestrator import ( build_melkov_agent, 
                                    extract_reply, 
                                    extract_tool_calls )
from app.agent.readings import Reading
from app.config import (
    CORS_ORIGINS,
    MAX_HISTORY_MESSAGES,
    MAX_IMAGE_B64_CHARS,
    MAX_SESSIONS,
    verify_config,
)
from app.rate_limit import (
    chat_global_limit,
    chat_rate_limit,
    global_key,
    GLOBAL_MESSAGE,
    limiter,
    PER_CLIENT_MESSAGE,
    rate_limit_exceeded_handler,
)
from app.routers.artwork import router as artwork_router
from app.routers.health import router as health_router
from app.routers.style import router as style_router
from app.tools.art_style_identifier import StyleIdentification, identify_art_style
from app.utils.image_utils import base64_to_pil
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallLog
from slowapi.errors import RateLimitExceeded
 
logging.basicConfig(level=logging.INFO, 
                    format="%(levelname)s %(name)s: %(message)s"
                    )

logger = logging.getLogger("melkov")

@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Validate configuration on boot, so a missing key fails here."""
    for warning in verify_config():
        
        logger.warning(warning)
        
    logger.info("Melkov ready.")
    yield


app = FastAPI(title="Melkov — Art Agent API", lifespan=_lifespan)

# /chat is rate limited per client IP and globally per day: every turn spends
# Anthropic tokens and GPU/API quota. See app/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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

# Mounts POST /artwork/read: fills the readings cache when an upload lands, so
# the first /chat on a new image finds the description and scores already
# inlined and skips both the VLM wait and the tool round-trip.
app.include_router(artwork_router)

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
@limiter.limit(chat_global_limit, 
               key_func=global_key, 
               error_message=GLOBAL_MESSAGE)
@limiter.limit(chat_rate_limit, 
               error_message=PER_CLIENT_MESSAGE)
def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Run one conversational turn.

    Args:
        request: The raw HTTP request; slowapi reads the client address from it.
        payload: The user's message, session id, and optional image.

    Returns:
        Melkov's reply plus any artifacts the tools produced.

    Raises:
        HTTPException: 413 if the attached image is too large, 502 if the
            turn fails outright. A rate limit answers 429 before the body runs.
    """
    if payload.image_base64 and len(payload.image_base64) > MAX_IMAGE_B64_CHARS:
        
        raise HTTPException(
            status_code=413,
            detail="Attached image is too large; please send a smaller one.",
        )

    history = _get_history(payload.session_id)

    # An upload replaces the artwork in the frame; silence keeps it. The
    # frontend sends the image once, so a turn with no bytes still has the
    # artwork — and everything the tools already said about it — in front of
    # it through the cached reading.
    reading: Reading | None
    
    if payload.image_base64:
        reading = readings.remember(payload.session_id, 
                                    payload.image_base64)
        
    else:
        reading = readings.current(payload.session_id)

    agent, artifacts = build_melkov_agent(reading=reading)

    try:
        result = agent.invoke(
            {"messages": [*history, 
                          HumanMessage(content=payload.message)
                          ]}
        )
    except Exception as error:  # noqa: BLE001
        # The detail is logged, never returned: exception text from the model
        # provider can carry request URLs and key fragments.
        logger.exception("Turn failed for session %s", 
                         payload.session_id)
        
        raise HTTPException(
            status_code=502,
            detail=f"Melkov could not complete that turn ({type(error).__name__}).",
        ) from error

    messages: list[BaseMessage] = result["messages"]
    reply = extract_reply(messages)
    _log_token_usage(payload.session_id, messages)

    # Only the user/assistant text is retained. Tool call and result messages
    # are dropped: they are large, and replaying them would invite the model
    # to treat stale tool output as current.
    history.append(HumanMessage(content=payload.message))
    history.append(AIMessage(content=reply))
    del history[:-MAX_HISTORY_MESSAGES]

    return ChatResponse(
        reply=reply,
        session_id=payload.session_id,
        tools_used=[
            ToolCallLog(tool=name, 
                        input_summary=summary
                        )
            for name, summary in extract_tool_calls(messages)
        ],
        generated_image_base64=artifacts["generated_image_b64"],
        met_results=artifacts["met_results"],
        louvre_results=artifacts["louvre_results"],
        british_museum_results=artifacts["british_museum_results"],
        cleveland_results=artifacts["cleveland_results"],
        art_advice=artifacts["art_advice"],
        gallery_results=artifacts["gallery_results"],
        style_analysis=artifacts["style_analysis"] or _classify_or_none(reading),
        vlm_description=artifacts["vlm_description"],
    )


def _log_token_usage(session_id: str, 
                     messages: list[BaseMessage]
                     ) -> None:
    """Log the turn's token bill, split into cached and uncached input.

    One INFO line per turn. chached_read staying at zero across turns means
    prompt caching is not takingprefix too short, or a silent invalidator
    it is the only way to tell from outside. Never raises.
    """
    try:
        usage = {"input": 0, "output": 0, 
                 "cache_read": 0, 
                 "cache_creation": 0
                 }
        calls = 0
        for message in messages:
            
            meta = getattr(message, "usage_metadata", None)
            
            if not meta:
                continue
            
            calls += 1
            usage["input"] += meta.get("input_tokens", 0) or 0
            usage["output"] += meta.get("output_tokens", 0) or 0
            details = meta.get("input_token_details") or {}
            usage["cache_read"] += details.get("cache_read", 0) or 0
            usage["cache_creation"] += details.get("cache_creation", 0) or 0
            
        logger.info(
            "Tokens for session %s: %d LLM call(s), input=%d (cache_read=%d, "
            "cache_creation=%d), output=%d",
            session_id,
            calls,
            usage["input"],
            usage["cache_read"],
            usage["cache_creation"],
            usage["output"],
        )
        
    except Exception:  # noqa: BLE001 - a log line must never fail a turn
        logger.debug("Token usage unavailable for session %s", session_id)


def _classify_or_none(reading: Reading | None) -> StyleIdentification | None:
    """
    Score the artwork in the frame even when the agent declined to call the tool.

    The prompt asks Melkov to always classify an attachment, but a prompt
    instruction is a request the model can decline — and the confidence panel
    would then sit empty. Scores already in the cache are reused; otherwise
    this is a local CPU pass with no API call, written back to the cache so
    it runs once per image. Every failure is swallowed: it must never turn a
    good turn into a 502.

    Args:
        reading: The artwork in the frame, or None.

    Returns:
        The classifier's answer, or None when there is nothing to score
        or scoring failed.
    """
    if reading is None:
        return None
    
    if reading.style is not None:
        return reading.style

    try:
        reading.style = identify_art_style(base64_to_pil(reading.image_b64))

    except Exception:  # noqa: BLE001 - the panel degrades, the turn does not
        logger.exception("Backstop classification failed")
        return None

    return reading.style


@app.delete("/session/{session_id}")
def clear_session(session_id: str) -> dict[str, str]:
    """Forget one conversation.

    Args:
        session_id: The conversation to drop.

    Returns:
        Whether a session was actually removed.
    """
    existed = _SESSIONS.pop(session_id, None) is not None
    
    readings.forget_session(session_id)
    
    return {
        "status": "cleared" if existed else "not found",
            "session_id": session_id
            }
