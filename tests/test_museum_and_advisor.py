from __future__ import annotations

from typing import Any

import pytest
import requests
import responses

from app.tools import artist_advisor, wikidata_museum
from app.tools.british_museum_search import british_museum_search
from app.tools.louvre_search import LOUVRE, louvre_search


def _binding(title: str, artist: str | None = None, image: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "item": {"value": "http://www.wikidata.org/entity/Q1"},
        "itemLabel": {"value": title},
        "inception": {"value": "1830-01-01T00:00:00Z"},
    }
    if artist:
        row["creatorLabel"] = {"value": artist}
    if image:
        row["image"] = {"value": image}
    return row


def test_sparql_query_escapes_quotes_and_scopes_to_museum() -> None:
    query = wikidata_museum.build_sparql_query(LOUVRE, 'Say "hi"\nthere', 5)
    assert f"wd:{LOUVRE.qid}" in query
    assert 'LCASE("Say \\"hi\\" there")' in query
    assert "LIMIT 5" in query


@responses.activate
def test_museum_search_parses_bindings_and_falls_back_to_entity_url() -> None:
    responses.get(
        wikidata_museum.WIKIDATA_SPARQL_ENDPOINT,
        json={"results": {"bindings": [_binding("Liberty", "Delacroix", "https://img/1.jpg")]}},
    )
    out = louvre_search("Delacroix", limit=99)
    assert out["source"] == "louvre" and "error" not in out
    work = out["results"][0]
    assert work["artist"] == "Delacroix" and work["image_url"] == "https://img/1.jpg"
    assert work["object_url"] == "http://www.wikidata.org/entity/Q1"
    assert "LIMIT 20" in responses.calls[0].request.url.replace("+", " ").replace("%20", " ")


@responses.activate
def test_museum_search_reports_failures_instead_of_raising() -> None:
    responses.get(wikidata_museum.WIKIDATA_SPARQL_ENDPOINT, body=requests.exceptions.Timeout())
    responses.get(wikidata_museum.WIKIDATA_SPARQL_ENDPOINT, status=503)
    responses.get(wikidata_museum.WIKIDATA_SPARQL_ENDPOINT, body="not json")

    timed_out = british_museum_search("x")
    refused = british_museum_search("x")
    garbled = british_museum_search("x")

    assert timed_out["results"] == [] and "timed out" in timed_out["error"]
    assert "request failed" in refused["error"]
    assert "malformed" in garbled["error"]
    assert all(r["source"] == "british_museum" for r in (timed_out, refused, garbled))


class _FakeYouTube:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.kwargs: dict[str, Any] = {}

    def search(self) -> "_FakeYouTube":
        return self

    def list(self, **kwargs: Any) -> "_FakeYouTube":
        self.kwargs = kwargs
        return self

    def execute(self) -> dict[str, Any]:
        return {"items": self.items}


def _video(channel: str, video_id: str = "v1", description: str = "d") -> dict[str, Any]:
    return {
        "id": {"videoId": video_id},
        "snippet": {"channelTitle": channel, "title": "T", "description": description},
    }


def test_art_advice_requires_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(artist_advisor, "YOUTUBE_DATA_API_KEY", "")
    with pytest.raises(RuntimeError, match="YOUTUBE_DATA_API_KEY"):
        artist_advisor.get_art_advice("x")


def test_art_advice_keeps_only_trusted_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeYouTube([
        _video("Random Guy", "bad"),
        _video("Marco Bucci Art", "a", "x" * 200),
        {"id": {}, "snippet": {"channelTitle": "Proko"}},
        _video("proko", "b"),
        _video("James Gurney", "c"),
        _video("Sinix Design", "d"),
    ])
    monkeypatch.setattr(artist_advisor, "YOUTUBE_DATA_API_KEY", "key")
    monkeypatch.setattr(artist_advisor, "build", lambda *a, **k: fake)

    out = artist_advisor.get_art_advice("skin tones")

    assert [v["url"][-1] for v in out] == ["a", "b", "c"]
    assert out[0]["description_snippet"].endswith("...")
    assert "Proko" in fake.kwargs["q"] and fake.kwargs["type"] == "video"


@responses.activate
def test_cleveland_search_parses_records_and_clamps_limit() -> None:
    from app.tools.cleveland_museum_search import CLEVELAND_API_URL, cleveland_search

    record = {
        "title": "The Red Kerchief", "creation_date": "c. 1868-73", "technique": "oil on fabric",
        "creators": [{"description": "Claude Monet (French, 1840-1926)"}],
        "images": {"web": {"url": "https://cdn/1958.39_web.jpg"}},
        "url": "https://clevelandart.org/art/1958.39",
    }
    responses.get(CLEVELAND_API_URL, json={"data": [record, {"title": "Bare", "images": None}]})

    out = cleveland_search("Monet", limit=99)

    assert out["source"] == "cleveland" and "error" not in out
    work, bare = out["results"]
    assert work["artist"].startswith("Claude Monet") and work["medium"] == "oil on fabric"
    assert work["image_url"] == "https://cdn/1958.39_web.jpg"
    assert bare["artist"] is None and bare["image_url"] is None
    url = responses.calls[0].request.url
    assert "limit=20" in url and "has_image=1" in url


@responses.activate
def test_cleveland_search_reports_failures_instead_of_raising() -> None:
    from app.tools.cleveland_museum_search import CLEVELAND_API_URL, cleveland_search

    responses.get(CLEVELAND_API_URL, body=requests.exceptions.Timeout())
    responses.get(CLEVELAND_API_URL, status=503)
    responses.get(CLEVELAND_API_URL, body="not json")
    responses.get(CLEVELAND_API_URL, json=["not", "an", "object"])

    outcomes = [cleveland_search("x") for _ in range(4)]

    assert all(o["results"] == [] for o in outcomes)
    assert "timed out" in outcomes[0]["error"]
    assert "request failed" in outcomes[1]["error"]
    assert "malformed" in outcomes[2]["error"] and "malformed" in outcomes[3]["error"]
