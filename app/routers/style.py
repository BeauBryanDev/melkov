
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.config import MAX_IMAGE_B64_CHARS
from app.schemas.style import StyleRequest
from app.schemas.chat import StyleIdentification
from app.tools.art_style_identifier import identify_art_style
from app.utils.image_utils import base64_to_pil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/style", tags=["style"])


@router.post("/identify", response_model=StyleIdentification)
def identify_style(request: StyleRequest) -> StyleIdentification:
    """
    Score one image against the classifier's fifteen styles CNN.

    Args:
        request: The image, base64, plus how many ranked styles to return.

    Returns:
        The ranked predictions, highest probability first.

    Raises:
        HTTPException: 413 if the image is too large, 400 if it cannot be
            decoded, 503 if the model artifacts are missing from ``models/``,
            502 if inference itself fails.
    """
    if len(request.image_base64) > MAX_IMAGE_B64_CHARS:
        
        raise HTTPException(
            status_code=413,
            detail="Attached image is too large; please send a smaller one.",
        )

    try:
        image = base64_to_pil(request.image_base64)
        
    except ValueError as error:
        # The only client-fixable failure here, so it is the only one whose
        # message is safe and useful to pass back verbatim.
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        return identify_art_style(image, top_k=request.top_k)
    
    except (FileNotFoundError, ValueError) as error:
        
        # A missing or mismatched artifact is a deployment fault, not a bad
        # request: 503 tells the UI to hide the panel rather than retry.
        logger.exception("Style classifier is unavailable")
        
        raise HTTPException(
            status_code=503,
            detail="The style classifier is not available on this server.",
        ) from error
        
    except Exception as error:  # noqa: BLE001
        logger.exception("Style classification failed")
        
        raise HTTPException(
            status_code=502,
            detail=f"Style classification failed ({type(error).__name__}).",
            
        ) from error
