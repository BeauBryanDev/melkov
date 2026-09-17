
from __future__ import annotations

from typing import Final

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import (
    ARTWORK_READ_RATE_LIMIT,
    CHAT_GLOBAL_DAILY_LIMIT,
    CHAT_RATE_LIMIT,
    RATE_LIMIT_ENABLED,
)

GLOBAL_KEY: Final[str] = "melkov-global"

PER_CLIENT_MESSAGE: Final[str] = (
    "Melkov needs a moment between questions. Please wait a little and ask again."
)
GLOBAL_MESSAGE: Final[str] = (
    "Melkov is resting for today - the atelier has reached its daily limit. "
    "Please come back tomorrow."
)

# Rate limits for the endpoints that spend money or GPU quota.

limiter = Limiter(key_func=get_remote_address, enabled=RATE_LIMIT_ENABLED)

# A /chat turn bills Anthropic tokens and can wake the ZeroGPU Space, call
# FLUX on NVIDIA credits and spend YouTube quota. On a public URL nothing else
# stops a script from looping it, so two limits apply to it: a per-client limit
# and a per-IP limit.

def chat_rate_limit() -> str:
    """Per-client limit string, read at call time so tests can override it."""
    return CHAT_RATE_LIMIT


def artwork_read_rate_limit() -> str:
    """Per-client limit for POST /artwork/read."""
    return ARTWORK_READ_RATE_LIMIT


def chat_global_limit() -> str:
    """Daily limit shared by every client."""
    return f"{CHAT_GLOBAL_DAILY_LIMIT}/day"


def global_key() -> str:
    """One bucket for all visitors (slowapi passes no request to a zero-arg key)."""
    return GLOBAL_KEY


def rate_limit_exceeded_handler(_: Request, 
                                exc: Exception
                                ) -> JSONResponse:
    """Answer 429 with a ``detail`` message the frontend can show as-is."""
    
    detail = exc.detail if isinstance(exc, RateLimitExceeded) else "Too many requests."
    
    return JSONResponse(status_code=429, 
                        content={"detail": detail}
                        )
