
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.agent import readings
from app.agent.readings import Reading
from app.config import MAX_IMAGE_B64_CHARS
from app.rate_limit import PER_CLIENT_MESSAGE, artwork_read_rate_limit, limiter
from app.schemas.artwork import ArtworkReadRequest, ArtworkReadResponse
from app.tools.art_style_identifier import identify_art_style
from app.tools.vlm_describe import describe_artwork
from app.utils.image_utils import base64_to_pil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artwork", tags=["artwork"])

# POST /artwork/read -> read the artwork when it lands, not when the first
# question arrives. it save several seconds of latency by not waiting for the
# VLM Space to warm up. in HF ZeroGPU, it takes about 85 s to start a Space
# (cold start) and about 10 s to warm it up. the first chat turn on a new image
# costs about 10 s, so the VLM Space is warmed up in the background.

@router.post("/read", response_model=ArtworkReadResponse)
@limiter.limit(artwork_read_rate_limit, error_message=PER_CLIENT_MESSAGE)
def read_artwork(request: Request, 
                 payload: ArtworkReadRequest
                 ) -> ArtworkReadResponse:
    """
    Describe and classify an upload, and remember it as the session's artwork.

    Args:
        request: The raw HTTP request; slowapi reads the client address from it.
        payload: The session and the image now in its frame.

    Returns:
        The VLM's description and the classifier's scores, served from the
        cache when this image has been read before.
        
    """
    if len(payload.image_base64) > MAX_IMAGE_B64_CHARS:
        raise HTTPException(
            status_code=413,
            detail="Attached image is too large; please send a smaller one.",
        )

    reading = readings.remember(payload.session_id,
                                payload.image_base64)

    # Every other caller (a chat turn on the same image) blocks here and then
    # finds the work done — one VLM call per image, whoever gets there first.
    with reading.lock:
        cached = reading.description is not None

        if not cached:
            _fill(reading)

    return ArtworkReadResponse(
        session_id=payload.session_id,
        vlm_description=reading.description or "",
        style_analysis=reading.style,
        cached=cached,
    )
    
    

# Helpers

def _fill(reading: Reading) -> None:
    """Run both image models on a reading that has not been read yet.

    The classifier runs first: it is local, takes about a second, and its
    scores stay in the cache even if the Space then fails.
    """
    try:
        image = base64_to_pil(reading.image_b64)
        
    except ValueError as error:
        raise HTTPException(status_code=400, 
                            detail=str(error)
                            ) from error

    if reading.style is None:
        try:
            reading.style = identify_art_style(image)
            
        except Exception:  # noqa: BLE001 - the panel degrades, the read does not
            logger.exception("Upload-time classification failed")

    try:
        reading.description = describe_artwork(image)
        
    except Exception as error:  # noqa: BLE001
        logger.exception("Upload-time VLM read failed")
        raise HTTPException(
            status_code=502,
            detail=f"Melkov could not read the artwork yet ({type(error).__name__}).",
        ) from error
