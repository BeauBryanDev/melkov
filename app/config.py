
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()


ANTHROPIC_API_KEY: Final[str] = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: Final[str] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
# Melkov Main LLM as Clade-Sonnet-5
_temperature_raw: Final[str] = os.getenv("LLM_TEMPERATURE", "").strip()
LLM_TEMPERATURE: Final[float | None] = (
    float(_temperature_raw) if _temperature_raw else None
)  

LLM_THINKING_ENABLED: Final[bool] = (
    os.getenv("LLM_THINKING_ENABLED", "false").strip().lower() == "true"
)
LLM_EFFORT: Final[str] = os.getenv("LLM_EFFORT", "low").strip()
LLM_MAX_TOKENS: Final[int] = int(os.getenv("LLM_MAX_TOKENS", "1500"))

# Melkov VLM fine-tuned Qwen2.5-VL-7B on a HF Space ZeroGPU
HF_TOKEN: Final[str] = os.getenv("HF_TOKEN", "")
MELKOV_VLM_SPACE: Final[str] = os.getenv("MELKOV_VLM_SPACE", "beaunix/melkov")
# The Space's only named endpoint. It takes a MultimodalTextbox payload  
# {"text": ..., "files": [...]} — not a bare file. Verified with view_api().
MELKOV_VLM_API_NAME: Final[str] = os.getenv("MELKOV_VLM_API_NAME", "/respond")
 
VLM_TIMEOUT: Final[float] = float(os.getenv("VLM_TIMEOUT", "180"))

# FLUX image generation via the NVIDIA build API  
NVIDIA_API_KEY: Final[str] = os.getenv("NVIDIA_API_KEY", "")
FLUX_INVOKE_URL: Final[str] = os.getenv(
    "FLUX_INVOKE_URL",
    "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b",
)
FLUX_TIMEOUT: Final[float] = float(os.getenv("FLUX_TIMEOUT", "120"))

#  MET Museum Open Access collection  
MET_API_BASE: Final[str] = "https://collectionapi.metmuseum.org/public/collection/v1"

# Art-style classifier (EfficientNetV2-S, ONNX, CPU)  
ART_STYLE_MODEL_DIR: Final[Path] = Path(
    os.getenv("ART_STYLE_MODEL_DIR", str(Path(__file__).resolve().parents[1] / "models"))
)
ART_STYLE_MODEL_PATH: Final[Path] = ART_STYLE_MODEL_DIR / "art_style_identifier.onnx"
ART_STYLE_CLASSES_PATH: Final[Path] = ART_STYLE_MODEL_DIR / "styles_classes.json"

# RAG store 
CHROMA_PERSIST_DIR: Final[str] = os.getenv("CHROMA_PERSIST_DIR", "./chroma_art_atelier")
# Empty lets sentence-transformers pick a GPU when one is present.
RAG_DEVICE: Final[str] = os.getenv("RAG_DEVICE", "")

# Session handling 

MAX_SESSIONS: Final[int] = int(os.getenv("MAX_SESSIONS", "500"))
MAX_HISTORY_MESSAGES: Final[int] = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

#  Request limits  
# Uploaded images arrive as base64 in the JSON body; base64 inflates by ~4/3,
# so this caps the decoded image at r~ 7.5 MB.
MAX_IMAGE_B64_CHARS: Final[int] = int(os.getenv("MAX_IMAGE_B64_CHARS", str(10_000_000)))

#  CORS  
# set CORS_ORIGINS to the real frontend origin before deploying.
CORS_ORIGINS: Final[list[str]] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]


def verify_config() -> list[str]:
    """
    Report configuration problems that would break the backend.
    Returns:
        Human-readable warnings for non-fatal gaps; empty when all set.
    Raises:
        RuntimeError: If ``ANTHROPIC_API_KEY`` is missing.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — add it to .env. Melkov cannot run "
            "without an orchestrator model."
        )

    warnings: list[str] = []
    if not NVIDIA_API_KEY:
        
        warnings.append("NVIDIA_API_KEY missing — image generation is disabled.")
        
    if not ART_STYLE_MODEL_PATH.is_file() or not ART_STYLE_CLASSES_PATH.is_file():
        warnings.append(
            f"Style classifier artifacts missing from {ART_STYLE_MODEL_DIR} — "
            "style classification is disabled."
        )
    if not os.path.isdir(CHROMA_PERSIST_DIR):
        
        warnings.append(
            f"CHROMA_PERSIST_DIR {CHROMA_PERSIST_DIR!r} not found — "
            "art-history retrieval is disabled."
        )
        
    return warnings
