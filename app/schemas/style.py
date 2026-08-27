
from __future__ import annotations

from pydantic import BaseModel, Field

from app.tools.art_style_identifier import DEFAULT_TOP_K
# this is art styles schema no css or html or js
# I know name can be misleading but it doesn not regard with css 

class StyleRequest(BaseModel):
    """One image to classify."""

    image_base64: str = Field(
        min_length=1,
        description="The artwork, base64, with or without a data: prefix.",
    )
    top_k: int = Field(
        default=DEFAULT_TOP_K,
        ge=1,
        le=15,
        description="How many ranked styles to return; 15 is every class.",
    )
