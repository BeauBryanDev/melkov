
from __future__ import annotations

import logging
import os
import tempfile
import threading
from typing import Any, Final

from gradio_client import Client, handle_file
from PIL import Image

from app.config import HF_TOKEN, MELKOV_VLM_API_NAME, MELKOV_VLM_SPACE, VLM_TIMEOUT
from app.utils.image_utils import resize_max_dim, save_temp_image
""" 
Melkov's eye — the fine-tuned Qwen2.5-VL-7B hosted on a HF Space.

``gradio_client`` here is the client-side SDK for calling that Space over
HTTP; no Gradio server runs in this process.logger = logging.getLogger(__name__)
""" 
logger = logging.getLogger(__name__)


_client: Client | None = None
_client_lock = threading.Lock()

# the VLM was trained at 896 px , hence this is the image size we send over HF
MAX_UPLOAD_DIM = 896


def _get_client() -> Client:
    """
    Return the shared Gradio client, connecting on first use.

    Returns:
        A connected client for the Melkov Space.
    """
    global _client
    if _client is None:
        
        with _client_lock:
            # Re-checked inside the lock: another thread may have connected
            # while this one was waiting.
            if _client is None:
                
                logger.info("Connecting to VLM Space %s", MELKOV_VLM_SPACE)
                # gradio_client 2.x renamed hf_token to `token`, and the
                # request timeout is only reachable through httpx_kwargs.
                # A ZeroGPU Space cold-starts on first call might take a while
                _client = Client(
                    MELKOV_VLM_SPACE,
                    token=HF_TOKEN or None,
                    httpx_kwargs={"timeout": VLM_TIMEOUT},
                )
                
    return _client


DEFAULT_INSTRUCTION: Final[str] = (
    "Describe and critique this artwork: its subject, composition, palette, "
    "handling of light, technique, and likely style or period."
)


def describe_artwork(image: Image.Image, 
                     instruction: str | None = None
                     ) -> str:
    """
    Describe an artwork with the fine-tuned VLM.

    The Space's endpoint is a Gradio ``MultimodalTextbox``, so the payload is
    a ``{"text": ..., "files": [...]}`` dict rather than a bare file — the
    instruction and the image travel together in one argument.

    Args:
        image: The artwork to look at.
        instruction: What to ask the VLM; a full description when omitted.

    Returns:
        The VLM model's description.

    Raises:
        RuntimeError: If the Space returns nothing usable.
    """
    image = resize_max_dim(image, max_dim=MAX_UPLOAD_DIM)

    # delete=False so the file is closed and readable by name on every
    # platform before upload; the finally block is what actually removes it.
    # Without that cleanup each described image leaked a PNG into /tmp.
    handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    handle.close()
    try:
        save_temp_image(image, handle.name)
        
        result = _get_client().predict(
            {
                "text": instruction or DEFAULT_INSTRUCTION,
                "files": [handle_file(handle.name)],
            },
            api_name=MELKOV_VLM_API_NAME,
        )
    finally:
        try:
            os.unlink(handle.name)
            
        except OSError:
            logger.warning("Could not remove temp file %s", handle.name)

    return _coerce_description(result)


def _coerce_description(result: Any) -> str:
    """
    Normalise whatever shape the Space returned into text.

    A Gradio endpoint may return a bare string, a dict, or a tuple of
    outputs depending on how the Space's function is declared, so the shape
    is discovered rather than assumed.

    Args:
        result: The raw ``predict`` return value.

    Returns:
        The description text.

    """
    if isinstance(result, (list, tuple)) and result:
        
        result = result[0]
        
    if isinstance(result, dict):
        
        for key in ("description", "text", "output", "caption"):
            
            value = result.get(key)
            
            if isinstance(value, str) and value.strip():
                
                return value.strip()
            
        raise RuntimeError(f"VLM returned no text field; keys were {list(result)}")
    
    if isinstance(result, str) and result.strip():
        
        return result.strip()
    
    raise RuntimeError(f"VLM returned an unusable response of type {type(result).__name__}")
