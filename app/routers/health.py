
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe, with a little operational detail.

    Returns:
        Status, the agent's name, and how many conversations are live in
        this process.
    """
    from app.main import _SESSIONS  # deferred: see module docstring

    return {"status": "ok", "agent": "melkov", "active_sessions": len(_SESSIONS)}
