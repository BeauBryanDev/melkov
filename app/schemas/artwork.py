
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.chat import StyleIdentification

# Request and response models for the upload-time artwork read."

class ArtworkReadRequest(BaseModel):
    """One uploaded image to read ahead of the conversation."""

    session_id: str = Field(min_length=1, 
                            description="Conversation identifier.")
    image_base64: str = Field(
        min_length=1,
        description="The artwork, base64, with or without a data: prefix.",
    )


class ArtworkReadResponse(BaseModel):
    """What the tools now know about the artwork in the frame."""

    session_id: str
    vlm_description: str = Field(description="The fine-tuned VLM's reading, verbatim.")
    style_analysis: StyleIdentification | None = Field(
        default=None,
        description="The classifier's scores; None only when the classifier failed.",
    )
    cached: bool = Field(
        description="True when the reading already existed and no model was run.",
    )
