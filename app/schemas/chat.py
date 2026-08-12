from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str
    session_id: str
    image_base64: Optional[str] = None  # imagen subida por el usuario, si aplica


class ToolCallLog(BaseModel):
    tool: str
    input_summary: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: List[ToolCallLog] = []
    generated_image_base64: Optional[str] = None
    met_results: Optional[List[dict]] = None
