
from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Final

from app.config import MAX_READINGS
from app.tools.art_style_identifier import StyleIdentification

_DATA_URL_SEPARATOR: Final[str] = ","

# Per-image cache of what Melkov's tools have already said about an artwork.
# Saving inference time, tokens, saves memory, saves the VLM Space. The cache is
# shared between sessions, so the frontend can't forget a conversation's
# artwork until the user has uploaded a new one. The backend can't forget a
# tool call on a turn that arrived without bytes, because the tool is still
# waiting for the image to arrive.
@dataclass(slots=True)
class Reading:
    """
    Everything known about one uploaded image.

    Attributes:
        image_hash: SHA-256 of the base64 payload; the cache key.
        image_b64: The payload itself, without a ``data:`` prefix, so a tool
            can still run on a turn that carried no bytes.
        description: The VLM's reading, once ``describe_artwork`` has run.
        style: The classifier's scores, once anything has classified it.
        lock: Serialises the expensive fills. The upload-time read and a
            chat turn can race on the same image; whoever loses the race
            waits and then finds the description already there, so the VLM
            Space is woken once per image, never twice.
    """
    image_hash: str
    image_b64: str
    description: str | None = None
    style: StyleIdentification | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, 
                                 repr=False, compare=False)


_READINGS: OrderedDict[str, Reading] = OrderedDict()
_SESSION_IMAGE: dict[str, str] = {}


def image_hash(image_b64: str) -> str:
    """Hash an upload so identical images share one reading.

    Args:
        image_b64: Base64 payload, with or without a ``data:`` prefix.

    Returns:
        Hex SHA-256 of the bare payload.
    """
    return hashlib.sha256(_strip_prefix(image_b64).encode("ascii", "ignore")).hexdigest()

# The cache is shared between sessions, so the frontend can't forget a
# conversation's artwork until the user has uploaded a new one. The backend
# can't forget a tool call on a turn that arrived without bytes, because the
# tool is still waiting for the image to arrive.
def remember(session_id: str, 
             image_b64: str
             ) -> Reading:
    """Record that a session's frame now holds this image.

    Args:
        session_id: The conversation the image was uploaded to.
        image_b64: The uploaded payload.

    Returns:
        The reading for this image, new or reused.
    """
    key = image_hash(image_b64)
    reading = _READINGS.get(key)
    
    if reading is None:
        
        reading = Reading(image_hash=key, 
                          image_b64=_strip_prefix(image_b64)
                          )
        
        _READINGS[key] = reading
        
        while len(_READINGS) > MAX_READINGS:
            
            _READINGS.popitem(last=False)
            
    else:
        _READINGS.move_to_end(key)
        
    _SESSION_IMAGE[session_id] = key
    
    return reading


def current(session_id: str) -> Reading | None:
    """Return the reading for the artwork in a session's frame, if any.

    Args:
        session_id: The conversation asking.

    Returns:
        The reading, or None when the session has never uploaded an image
        or its reading has since been evicted.
    """
    key = _SESSION_IMAGE.get(session_id)
    
    if key is None:
        return None
    
    reading = _READINGS.get(key)
    
    if reading is None:
        # Evicted under the session's feet: forget the dangling pointer so
        # the frontend's next upload starts clean.
        _SESSION_IMAGE.pop(session_id, None)
        return None
    
    _READINGS.move_to_end(key)
    
    return reading


def forget_session(session_id: str) -> None:
    """
    Drop a session's link to its artwork; the reading itself may be shared.

    Args:
        session_id: The conversation being cleared.
    """
    _SESSION_IMAGE.pop(session_id, None)


def clear() -> None:
    """Empty both structures. For tests and for a deliberate reset."""
    _READINGS.clear()
    _SESSION_IMAGE.clear()


def _strip_prefix(image_b64: str) -> str:
    
    if image_b64.startswith("data:") and _DATA_URL_SEPARATOR in image_b64:
        
        return image_b64.split(_DATA_URL_SEPARATOR, 1)[1]
    
    return image_b64
