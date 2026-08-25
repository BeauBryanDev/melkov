
from __future__ import annotations

import logging
import random
from typing import Any, Final

import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import FLUX_INVOKE_URL, FLUX_TIMEOUT, NVIDIA_API_KEY
from app.utils.image_utils import base64_to_pil

"""Image generation through FLUX on the NVIDIA build API.
[ only for academic  purpuses and not for production use]
TODO:  keep an eyes on NVIIDA build API, becuase they usually changes
their endpoint"""

logger = logging.getLogger(__name__)

MAX_SEED: Final[int] = 2**31 - 1
# The API rejects anything longer with a 422 "String should have at most 800
# characters". An LLM writing a rich visual prompt overruns this easily, so
# it is enforced here rather than trusted to the caller.
MAX_PROMPT_CHARS: Final[int] = 800
# Keys that have held the base64 payload across API revisions, in the order
# they are worth trying.
_IMAGE_KEYS: Final[tuple[str, ...]] = ("image", "b64_json", "base64")


def _session() -> requests.Session:
    """Build a session that retries transient upstream failures.

    Returns:
        A configured session.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    
    return session


def generate_artwork(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    seed: int | None = None,
    init_image_b64: str | None = None,
) -> Image.Image:
    """Generate an artwork from a text prompt.

    Args:
        prompt: The visual description to render.
        width: Output width in pixels.
        height: Output height in pixels.
        steps: Diffusion steps; the klein models are tuned for very few.
        seed: Fixed seed for reproducibility; random when omitted.
        init_image_b64: Optional base64 image to condition the generation.

    Returns:
        The generated image.

    Raises:
        RuntimeError: If the key is unset or the response holds no image.
        requests.HTTPError: If the API rejects the request.
    """
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not set — image generation is disabled.")

    payload: dict[str, Any] = {
        "prompt": _fit_prompt(prompt),
        "width": width,
        "height": height,
        "seed": seed if seed is not None else random.randint(0, MAX_SEED),
        "steps": steps,
    }
    # The `image` key must be absent for text-to-image. Sending a placeholder
    # empty string is rejected with 422 "Image has been provided in the
    # invalid form" rather than being treated as "no image".
    if init_image_b64:
        
        payload["image"] = [init_image_b64]

    response = _session().post(
        
        FLUX_INVOKE_URL,
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "application/json",
        },
        json=payload,
        timeout=FLUX_TIMEOUT,
    )
    response.raise_for_status()

    image_b64 = _find_image(response.json())
    
    if not image_b64:
        
        raise RuntimeError(
            "FLUX response contained no image payload; the API envelope may "
            "have changed."
        )
    return base64_to_pil(image_b64)


def _fit_prompt(prompt: str) -> str:
    """Trim a prompt to the API's length limit, cutting at a clause break.

    Truncating mid-word produces a stray fragment the model then tries to
    render, so the cut is made at the last sentence or clause boundary in
    the final quarter of the allowance where one exists.

    Args:
        prompt: The requested prompt.

    Returns:
        A prompt within the API's limit.
    """
    prompt = prompt.strip()
    
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt

    head = prompt[:MAX_PROMPT_CHARS]
    for separator in (". ", "; ", ", "):
        cut = head.rfind(separator)
        
        if cut > MAX_PROMPT_CHARS * 0.75:
            
            logger.info("Trimmed prompt from %d to %d chars", len(prompt), cut)
            return head[:cut].rstrip(" ,;")
        
    return head.rsplit(" ", 1)[0]


def _find_image(body: Any, depth: int = 0) -> str | None:
    """Search a decoded response for a base64 image payload.

    Walks the structure instead of indexing a fixed path, since the envelope
    varies by model and revision.

    Args:
        body: Decoded JSON, at any nesting level.
        depth: Current recursion depth, to bound pathological payloads.

    Returns:
        The base64 string, or None if the payload holds no image.
    """
    if depth > 4:
        
        return None
    
    if isinstance(body, dict):
        
        for key in _IMAGE_KEYS:
            
            value = body.get(key)
            # A long string here is the payload; a short one is a URL or a
            # format name such as "png".
            if isinstance(value, str) and len(value) > 256:
                
                return value
            
        for value in body.values():
            
            found = _find_image(value, depth + 1)
            
            if found:
                
                return found
            
    elif isinstance(body, list):
        
        for item in body:
            
            found = _find_image(item, depth + 1)
            
            if found:
                
                return found
            
            
    return None
