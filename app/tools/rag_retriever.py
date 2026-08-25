
from __future__ import annotations

from typing import Any

from RAG.retrieval import Hit, load_model, open_collection, search
# this is the actual RAG client retriver
from app.config import CHROMA_PERSIST_DIR, RAG_DEVICE
"""
Art-history RAG tool — the query side of the ChromaDB corpus.

Thin wrapper over ``RAG.retrieval``, which owns the query convention for
this collection: the ``search_query:`` prefix that ``nomic-embed-text-v1.5``
expects, and the MMR re-rank that stops the 80-word chunk overlap from
filling the whole result set with neighbours of one passage. Neither is
optional and neither fails loudly when missing — they just return worse
context — so this module deliberately does not reimplement retrieval with
a generic vector-store client.

The model and the collection are loaded once per process, on first query.
"""
_model: Any | None = None
_collection: Any | None = None


def _get_model() -> Any:
    """Return the process-wide embedding model, loading it on first use."""
    global _model
    
    if _model is None:
        
        _model = load_model(device=RAG_DEVICE or None)
        
    return _model


def _get_collection() -> Any:
    """Return the process-wide Chroma collection, opening it on first use."""
    global _collection
    
    if _collection is None:
        
        _collection = open_collection(CHROMA_PERSIST_DIR)
        
    return _collection


def _format(hit: Hit) -> str:
    """
    Render one hit as a cited passage for the agent to read.
    """
    return f"[Source: {hit.citation}]\n\n{hit.text}"


def query_art_history(question: str, 
                      k: int = 4
                      ) -> str:
    """
    Retrieve relevant context from the art-history corpus.

    Args:
        question: A natural-language art-history or art-theory question.
        k: How many chunks to return.

    Returns:
        The retrieved passages, each prefixed with its citation, or a
        short notice when nothing matched.
    """
    hits = search(question, _get_collection(), _get_model(), n_results=k)

    if not hits:
        return "No relevant passages found in the art-history corpus."

    return "\n\n---\n\n".join(_format(hit) for hit in hits)
