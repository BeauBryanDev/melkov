from __future__ import annotations

from typing import Any

import pytest

from app.tools import rag_retriever
from RAG.retrieval import Hit


def _hit(text: str = "Chiaroscuro models form through light.") -> Hit:
    return Hit(
        chunk_id="c1",
        text=text,
        distance=0.12,
        metadata={"book_title": "Art and Illusion", "pagina_aprox": 40, "pagina_fin": 42},
    )


def test_query_delegates_once_and_memoises(
    monkeypatch: pytest.MonkeyPatch, reset_rag: None
) -> None:
    loads = {"model": 0, "collection": 0}
    calls: list[dict[str, Any]] = []

    def fake_load_model(device: str | None = None) -> object:
        loads["model"] += 1
        return object()

    def fake_open_collection(directory: str) -> object:
        loads["collection"] += 1
        return object()

    monkeypatch.setattr(rag_retriever, "load_model", fake_load_model)
    monkeypatch.setattr(rag_retriever, "open_collection", fake_open_collection)

    def fake_search(question: str, collection: Any, model: Any, n_results: int = 4) -> list[Hit]:
        calls.append({"question": question, "n_results": n_results})
        return [_hit()]

    monkeypatch.setattr(rag_retriever, "search", fake_search)

    rag_retriever.query_art_history("what is chiaroscuro?", k=2)
    rag_retriever.query_art_history("what is sfumato?", k=2)

    assert calls[0] == {"question": "what is chiaroscuro?", "n_results": 2}
    # The embedding model and the store load once per process, not per query.
    assert loads == {"model": 1, "collection": 1}


def test_empty_store_returns_a_message_and_hits_are_cited(
    monkeypatch: pytest.MonkeyPatch, reset_rag: None
) -> None:
    monkeypatch.setattr(rag_retriever, "load_model", lambda device=None: object())
    monkeypatch.setattr(rag_retriever, "open_collection", lambda directory: object())
    monkeypatch.setattr(rag_retriever, "search", lambda *a, **k: [])

    assert "No relevant passages" in rag_retriever.query_art_history("anything")

    formatted = rag_retriever._format(_hit())
    assert formatted.startswith("[Source: Art and Illusion, pp.40-42]")
    assert "Chiaroscuro models form through light." in formatted
