import os
from dotenv import load_dotenv

load_dotenv()
 
# Anthropic — the orchestrator LLM. No OpenAI anywhere in this project.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

 
HF_TOKEN = os.getenv("HF_TOKEN", "")
 # Hugging Face
MELKOV_VLM_SPACE = os.getenv("MELKOV_VLM_SPACE", "beaunix/melkov")
 
MELKOV_VLM_API_NAME = os.getenv("MELKOV_VLM_API_NAME", "/predict")

# -FLUX via NVIDIA build API 
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
FLUX_INVOKE_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

# -MET Museum Collection API 
# The Metropolitan Museum of Art Open Access Collection API.
MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

#  RAG local (ChromaDB) 
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_art_atelier")

# The embedding model and collection name are NOT configured here: they are
# properties of the store that was already built, so they live next to the
# query convention in RAG/retrieval.py (EMBED_MODEL, COLLECTION_NAME).
# Overriding them from the environment could only ever mismatch the vectors.

# Torch device for the embedding model; empty lets sentence-transformers
# pick the GPU when one is present.
RAG_DEVICE = os.getenv("RAG_DEVICE", "")
