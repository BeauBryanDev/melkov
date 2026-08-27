
from __future__ import annotations

import base64
import binascii
import io
from typing import Final
# Image conversions shared by the VLM and generation tools
from PIL import Image

# Browsers send uploads as `data:image/png;base64,....`; the API also accepts
# a bare payload, so the prefix is stripped when present rather than required.
_DATA_URL_SEPARATOR: Final[str] = ","


def base64_to_pil(b64_string: str) -> Image.Image:
    """
    Decode a base64 payload into an RGB image.

    Args:
        b64_string: Raw base64, with or without a ``data:`` URL prefix.

    Returns:
        The decoded image, converted to RGB so downstream code never has to
        handle palette or alpha modes.

    Raises:
        ValueError: If the string is not valid base64 or not an image.
    """
    if b64_string.startswith("data:") and _DATA_URL_SEPARATOR in b64_string:
        b64_string = b64_string.split(_DATA_URL_SEPARATOR, 1)[1]

    try:
        raw = base64.b64decode(b64_string, validate=False)
        
    except (binascii.Error, ValueError) as error:
        raise ValueError("Attachment is not valid base64.") from error

    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    
    except OSError as error:
        raise ValueError("Attachment is not a readable image.") from error


def pil_to_base64(image: Image.Image, 
                  fmt: str = "PNG"
                  ) -> str:
    """Encode an image as base64, without a ``data:`` prefix.

    Args:
        image: The image to encode.
        fmt: A Pillow format name.

    Returns:
        The base64 payload.
    """
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def save_temp_image(image: Image.Image, 
                    path: str
                    ) -> str:
    """Write an image to a path, for tools that need a real file.

    Args:
        image: The image to write.
        path: Destination path.

    Returns:
        The path written to.
    """
    image.save(path)
    return path


def resize_max_dim(image: Image.Image, 
                   max_dim: int = 1024
                   ) -> Image.Image:
    """Shrink an image to fit a maximum edge length, preserving aspect ratio.

    Images already within the limit are returned untouched rather than
    re-encoded.

    Args:
        image: The image to fit.
        max_dim: Maximum length of the longer edge, in pixels.

    Returns:
        The fitted image.
    """
    width, height = image.size
    if max(width, height) <= max_dim:
        return image
    
    scale = max_dim / max(width, height)
    
    return image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
