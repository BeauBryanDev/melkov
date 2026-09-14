
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

load_dotenv()

##  LLM Providers from Anthropic
ANTHROPIC_API_KEY: Final[str] = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: Final[str] = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
# Melkov Main Brain as Clade-Sonnet-5
_temperature_raw: Final[str] = os.getenv("LLM_TEMPERATURE", "").strip()
# LLM Settings: temperature, effort, max tokens, and thinking mode.
LLM_TEMPERATURE: Final[float | None] = (
    float(_temperature_raw) if _temperature_raw else None
)  
# SET  LOWER EFFORT ON CLAUDE-SONNET-5 TO SAVE TOKENS
LLM_EFFORT: Final[str] = os.getenv("LLM_EFFORT", "low").strip()
LLM_THINKING_ENABLED: Final[bool] = (
    os.getenv("LLM_THINKING_ENABLED", "false").strip().lower() == "true"
)
LLM_MAX_TOKENS: Final[int] = int(os.getenv("LLM_MAX_TOKENS", "1500"))
# Prompt caching: a top-level cache_control marks the last block of every
# request, so the tool schemas + system prompt + history read from cache on
# the next call (the second call of a tool turn, and every later turn). Set
# LLM_PROMPT_CACHE=false to switch it off without touching code.
LLM_PROMPT_CACHE: Final[bool] = (
    os.getenv("LLM_PROMPT_CACHE", "true").strip().lower() == "true"
)

# Melkov VLM fine-tuned Qwen2.5-VL-7B on a HF Space ZeroGPU
HF_TOKEN: Final[str] = os.getenv("HF_TOKEN", "")  # this is my VLM QloRA in HF Spaces
MELKOV_VLM_SPACE: Final[str] = os.getenv("MELKOV_VLM_SPACE", "beaunix/melkov")
# The Space's only named endpoint. It takes a MultimodalTextbox payload  
# {"text": ..., "files": [...]} — not a bare file. Verified with view_api().
MELKOV_VLM_API_NAME: Final[str] = os.getenv("MELKOV_VLM_API_NAME", "/respond")
# TODO: I MUST EDIT THE GRADIO SPACE CODE IN app.py TO DECREASE THE TOKEN LIMIT //DONE!
# MY VLM IS GIVING LONG RESPONSES, SO I NEED TO SET A LOWER TOKEN LIMIT
VLM_TIMEOUT: Final[float] = float(os.getenv("VLM_TIMEOUT", "180"))

# FLUX image generation via the NVIDIA build API  
NVIDIA_API_KEY: Final[str] = os.getenv("NVIDIA_API_KEY", "")
FLUX_INVOKE_URL: Final[str] = os.getenv(
    "FLUX_INVOKE_URL",
    "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b",
) # It change fron nvidia last week,  I had better check this evry week, nvidia is changing their API
FLUX_TIMEOUT: Final[float] = float(os.getenv("FLUX_TIMEOUT", "120")) # all time out

#  MET Museum Open Access collection  
MET_API_BASE: Final[str] = "https://collectionapi.metmuseum.org/public/collection/v1"

# Louvre / British Museum via Wikidata SPARQL (needs a descriptive User-Agent).
WIKIDATA_SPARQL_ENDPOINT: Final[str] = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT: Final[str] = os.getenv(
    "WIKIDATA_USER_AGENT",
    "Aegis-Art-Atelier-Melkov/1.0 (https://github.com/BeauBryanDev/)",
)
WIKIDATA_TIMEOUT: Final[float] = float(os.getenv("WIKIDATA_TIMEOUT", "20"))
MUSEUM_SEARCH_LIMIT: Final[int] = int(os.getenv("MUSEUM_SEARCH_LIMIT", "8"))

# Artist advisor (YouTube Data API v3). Optional.
YOUTUBE_DATA_API_KEY: Final[str] = os.getenv("YOUTUBE_DATA_API_KEY", "")
YOUTUBE_SEARCH_POOL: Final[int] = int(os.getenv("YOUTUBE_SEARCH_POOL", "10"))
YOUTUBE_MAX_RESULTS: Final[int] = int(os.getenv("YOUTUBE_MAX_RESULTS", "3"))

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
# Cached per-image readings (VLM description + style scores + the bytes), LRU.
# Each entry holds one upload's base64, so this bounds memory, not sessions.
MAX_READINGS: Final[int] = int(os.getenv("MAX_READINGS", "100"))

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

    if not YOUTUBE_DATA_API_KEY:
        warnings.append("YOUTUBE_DATA_API_KEY missing — painting-advice videos are disabled.")
        
    if not ART_STYLE_MODEL_PATH.is_file() or not ART_STYLE_CLASSES_PATH.is_file():
        warnings.append( # the CNN  must be at the root of the models folder
            f"Style classifier artifacts missing from {ART_STYLE_MODEL_DIR} — "
            "style classification is disabled."
        )
    if not os.path.isdir(CHROMA_PERSIST_DIR):
        
        warnings.append(
            f"CHROMA_PERSIST_DIR {CHROMA_PERSIST_DIR!r} not found — "
            "art-history retrieval is disabled."
        )
        
        
    return warnings
