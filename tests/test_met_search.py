from __future__ import annotations

from typing import Any

import pytest

from app.tools import met_search


def _met_object(object_id: int, **overrides: Any) -> dict[str, Any]:
    payload = {
        "objectID": object_id,
        "title": "  The Harvesters  ",
        "artistDisplayName": "Pieter Bruegel the Elder",
        "objectDate": "1565",
        "medium": "Oil on wood",
        "primaryImage": "https://images.metmuseum.org/full.jpg",
        "primaryImageSmall": "https://images.metmuseum.org/small.jpg",
        "isPublicDomain": True,
        "tags": [{"term": "Harvest"}, {"term": "Harvest"}, {"term": "Men"}],
        "objectURL": "https://www.metmuseum.org/art/collection/435809",
    }
    payload.update(overrides)
    return payload


def test_scalar_helpers_normalise_and_clamp() -> None:
    assert met_search._clean_string("  Vermeer  ") == "Vermeer"
    assert met_search._clean_string("   ") is None
    assert met_search._clean_string(None) is None
    assert met_search._clean_string(1565) == "1565"

    assert met_search._clamp_max_results(0) == 1
    assert met_search._clamp_max_results(99) == met_search.MAX_ALLOWED_RESULTS
    assert met_search._clamp_max_results(5) == 5
    assert met_search._clamp_max_results("many") == met_search.DEFAULT_MAX_RESULTS


def test_extract_tags_survives_unexpected_shapes() -> None:
    tags = met_search._extract_tags([{"term": "Harvest"}, {"term": "Harvest"}])
    assert tags == ["Harvest"]
    # Bare strings and junk carry no term, so they are dropped rather than raised on.
    assert met_search._extract_tags(["Harvest", 3, None]) == []
    assert met_search._extract_tags("Harvest") == []
    assert met_search._extract_tags(None) == []


def test_normalize_artwork_maps_and_filters() -> None:
    record = met_search._normalize_artwork(_met_object(435809))
    assert record is not None
    assert record["object_id"] == 435809
    assert record["title"] == "The Harvesters"
    assert record["artist"] == "Pieter Bruegel the Elder"
    assert record["image_url"] == "https://images.metmuseum.org/full.jpg"
    assert record["tags"] == ["Harvest", "Men"]

    assert met_search._normalize_artwork(_met_object(1, primaryImage="")) is None
    assert met_search._normalize_artwork(_met_object(1, objectID=None)) is None
    assert met_search._normalize_artwork(_met_object(1, isPublicDomain=False)) is None


def test_search_met_artworks_limits_dedupes_and_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = [1, 1, 2, 3, 4, 5]
    monkeypatch.setattr(met_search, "_search_object_ids", lambda *a, **k: ids)

    def fake_get_object(object_id: int) -> dict[str, Any] | None:
        if object_id == 2:
            return None
        if object_id == 3:
            return _met_object(3, primaryImage="")
        return _met_object(object_id)

    monkeypatch.setattr(met_search, "_get_object", fake_get_object)

    results = met_search.search_met_artworks("Bruegel", max_results=2)
    assert [item["object_id"] for item in results] == [1, 4]

    monkeypatch.setattr(met_search, "_search_object_ids", lambda *a, **k: [])
    assert met_search.search_met_artworks("nothing at all") == []
