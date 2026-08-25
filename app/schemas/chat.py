
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
"""Request and response models for the chat endpoint."""

class StylePrediction(BaseModel):
    """One row of the style classification chart."""

    label: str = Field(description="A style name from the classifier's 15 classes.")
    probability: float = Field(ge=0.0, le=1.0, description="Softmax weight, 0 to 1.")
    # it comes form y custom CNN Model EfficientNetV2-S x15 art style classifier

class StyleIdentification(BaseModel):
    """
    The style classifier's full answer for one image.

    """

    model: str = Field(
        default="melkov-art-style-cnn",
        description="Which classifier produced these scores.",
    )
    predictions: list[StylePrediction] = Field(
        default_factory=list,
        description="Ranked highest probability first.",
    )
    top_k: int = Field(description="How many predictions were requested.")


class ChatRequest(BaseModel):
    """One user turn."""

    message: str = Field(min_length=1, description="The user's message.")
    session_id: str = Field(min_length=1, description="Conversation identifier.")
    image_base64: str | None = Field(
        default=None,
        description="Image uploaded with this turn, base64, optional data: prefix.",
    )


class ToolCallLog(BaseModel):
    """A single tool invocation, for display and debugging."""

    tool: str
    input_summary: str


class ChatResponse(BaseModel):
    """Melkov's reply, plus anything the tools produced."""

    reply: str
    session_id: str
    tools_used: list[ToolCallLog] = Field(default_factory=list)
    generated_image_base64: str | None = None
    met_results: list[dict[str, Any]] | None = None
    vlm_description: str | None = Field(
        default=None,
        description=(
            "The fine-tuned VLM's description of the attached image text . "
            "Present only when the vision tool ran and succeeded."
        ),
    )
    style_analysis: StyleIdentification | None = Field(
        default=None,
        description=(
            "The style classifier's top-k scores for the attached image. "
            "Present only when the classifier tool ran and succeeded; the "
            "confidence panel stays empty otherwise."
        ),  
    )
