"""Shared retrieval helpers for the Art-Atelier ChromaDB collection.

Used by the Phase 6 validation script and, later, by the FastAPI backend
that serves the Melkov agent — so the query-side embedding convention
lives in exactly one place.

The embedding model is asymmetric: passages are encoded with a
``search_document:`` prefix at ingestion time and questions with a
``search_query:`` prefix at query time. Mixing the two up does not raise
an error, it just quietly returns worse results, which is why both
prefixes are defined here rather than at each call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

EMBED_MODEL: Final[str] = "nomic-ai/nomic-embed-text-v1.5"
COLLECTION_NAME: Final[str] = "art_atelier_corpus"
DOC_PREFIX: Final[str] = "search_document: "
QUERY_PREFIX: Final[str] = "search_query: "


@dataclass(slots=True)
class Hit:
    """One retrieved chunk.

    Attributes:
        chunk_id: The chunk's unique id.
        text: The chunk body.
        distance: Cosine distance; lower is closer.
        metadata: The chunk's stored metadata.
    """

    chunk_id: str
    text: str
    distance: float
    metadata: dict[str, Any]

    @property
    def book_id(self) -> str:
        """The source book's identifier."""
        return str(self.metadata.get("book_id", "?"))

    @property
    def citation(self) -> str:
        """A short human-readable source reference.

        Cites a page range when the chunk spans pages, and omits the
        chapter entirely when none was detected rather than printing a
        placeholder a reader would mistake for a real heading.
        """
        start = self.metadata.get("pagina_aprox")
        end = self.metadata.get("pagina_fin", start)
        pages = f"p.{start}" if start == end or end is None else f"pp.{start}-{end}"
        reference = f"{self.metadata.get('book_title', '?')}, {pages}"
        chapter = self.metadata.get("capitulo")
        return f"{reference} [{chapter}]" if chapter else reference


def collection_exists(client: Any, name: str = COLLECTION_NAME) -> bool:
    """Check whether a collection exists, across ChromaDB versions.

    ChromaDB 0.6 changed ``list_collections`` to return names rather than
    collection objects, so both shapes are handled.

    Args:
        client: A ChromaDB client.
        name: Collection name to look for.

    Returns:
        True when the collection is present.
    """
    existing = client.list_collections()
    names = {c if isinstance(c, str) else c.name for c in existing}
    return name in names


def load_model(device: str | None = None) -> Any:
    """Load the embedding model.

    Args:
        device: Torch device string; ``None`` lets sentence-transformers
            pick the GPU when one is available.

    Returns:
        A loaded SentenceTransformer.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL, trust_remote_code=True, device=device)


def open_collection(persist_dir: Path | str) -> Any:
    """Open the persistent collection for querying.

    Args:
        persist_dir: Directory holding the persisted Chroma store.

    Returns:
        The Chroma collection.

    Raises:
        SystemExit: If the store has not been built yet.
    """
    import chromadb

    client = chromadb.PersistentClient(path=str(persist_dir))
    if not collection_exists(client):
        raise SystemExit(
            f"collection {COLLECTION_NAME!r} not found in {persist_dir} — "
            "run colab_embed_ingest.py first"
        )
    return client.get_collection(COLLECTION_NAME)


def _mmr_select(
    embeddings: list[list[float]], count: int, diversity: float
) -> list[int]:
    """Pick indices by maximal marginal relevance.

    Consecutive chunks share an 80-word overlap, so the nearest neighbours
    of a good match are usually its own neighbours in the book. Ranking on
    similarity alone therefore spends the whole result set on one passage.
    MMR trades a little relevance for coverage.

    Args:
        embeddings: Candidate vectors, ordered by ascending distance.
        count: How many indices to select.
        diversity: 0 keeps pure relevance ordering, 1 maximises spread.

    Returns:
        Selected candidate indices, best first.
    """
    import numpy as np

    matrix = np.array(embeddings, dtype=float)
    # Candidates arrive sorted by distance, so rank stands in for relevance
    # and needs no separate query-similarity computation.
    relevance = np.linspace(1.0, 0.0, num=len(matrix))
    selected: list[int] = [0]
    while len(selected) < min(count, len(matrix)):
        best_index, best_score = -1, -np.inf
        for index in range(len(matrix)):
            if index in selected:
                continue
            redundancy = max(float(matrix[index] @ matrix[chosen]) for chosen in selected)
            score = (1 - diversity) * relevance[index] - diversity * redundancy
            if score > best_score:
                best_index, best_score = index, score
        if best_index < 0:
            break
        selected.append(best_index)
    return selected


def search(
    question: str,
    collection: Any,
    model: Any,
    n_results: int = 5,
    where: dict[str, Any] | None = None,
    diversity: float = 0.35,
    fetch_multiplier: int = 4,
) -> list[Hit]:
    """Retrieve the chunks most relevant to a question.

    Over-fetches, then re-ranks with MMR so the results are not several
    near-copies of the same passage.

    Args:
        question: A natural-language question.
        collection: The Chroma collection to search.
        model: The loaded embedding model.
        n_results: How many chunks to return.
        where: Optional metadata filter, e.g. ``{"book_id": "itten_art_of_color"}``.
        diversity: MMR weight; 0 disables diversification.
        fetch_multiplier: Candidate pool size, as a multiple of ``n_results``.

    Returns:
        Hits ordered best first.
    """
    vector = model.encode(
        [QUERY_PREFIX + question], normalize_embeddings=True
    )[0].tolist()
    pool = n_results * fetch_multiplier if diversity > 0 else n_results
    result = collection.query(
        query_embeddings=[vector],
        n_results=min(pool, max(collection.count(), 1)),
        where=where,
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    hits = [
        Hit(
            chunk_id=chunk_id,
            text=document,
            distance=float(distance),
            metadata=metadata,
        )
        for chunk_id, document, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        )
    ]
    if diversity <= 0 or len(hits) <= n_results:
        return hits[:n_results]

    order = _mmr_select(
        [list(embedding) for embedding in result["embeddings"][0]],
        n_results,
        diversity,
    )
    return [hits[index] for index in order]
