
from __future__ import annotations

from typing import Any, Final

import requests

from app.config import (
    CLEVELAND_API_URL,
    CLEVELAND_TIMEOUT,
    MUSEUM_SEARCH_LIMIT,
    MUSEUM_USER_AGENT,
)

SOURCE: Final[str] = "cleveland"
DISPLAY_NAME: Final[str] = "Cleveland Museum of Art"
MAX_LIMIT: Final[int] = 20


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

# Search the Cleveland Museum of Art through its own Open Access REST API.

def _parse_artwork(artwork: dict[str, Any]) -> dict[str, Any]:
    """Convert one CMA artwork record into the shared museum-result shape."""
    creators = artwork.get("creators") or []
    first_creator = _as_dict(creators[0]) if isinstance(creators, list) and creators else {}
    web_image = _as_dict(_as_dict(artwork.get("images")).get("web"))

    return {
        "title": artwork.get("title"),
        "artist": first_creator.get("description"),
        "date": artwork.get("creation_date"),
        "medium": artwork.get("technique"),
        "image_url": web_image.get("url"),
        "object_url": artwork.get("url"),
        "museum": DISPLAY_NAME,
    }


def cleveland_search(
    query: str,
    limit: int = MUSEUM_SEARCH_LIMIT,
    only_with_image: bool = True,
    artwork_type: str | None = None,
) -> dict[str, Any]:
    """Search Cleveland Museum of Art artworks by keyword.

    Args:
        query: Free-text search term, matched against title, creator and
            description.
        limit: Maximum number of results, clamped to ``1..MAX_LIMIT``.
        only_with_image: When True (default), only artworks with a web image -
            Melkov always needs something to show.
        artwork_type: Optional CMA type filter ("Painting", "Drawing", ...).
            Unset by default so valid non-painting results are not dropped.

    Returns:
        {"source": "cleveland", "query": ..., "results": [{"title",
        "artist", "date", "medium", "image_url", "object_url", "museum"},
        ...]}. 
    On any failure results is empty and error says why 
    never fabricated results.
    """
    params: dict[str, Any] = {"q": query, "limit": max(1, min(limit, MAX_LIMIT))}
    if only_with_image:
        params["has_image"] = 1
        
    if artwork_type:
        params["type"] = artwork_type

    def failure(message: str) -> dict[str, Any]:
        return {
            "source": SOURCE, 
            "query": query, 
            "results": [], 
            "error": message
            }
        

    try:
        response = requests.get(
            CLEVELAND_API_URL,
            params=params,
            headers={"User-Agent": MUSEUM_USER_AGENT},
            timeout=CLEVELAND_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        
    except requests.exceptions.Timeout:
        return failure(f"{DISPLAY_NAME} search timed out.")
    # JSONDecodeError is a RequestException: catch it first, or a garbled body
    # reads as a network failure.
    except (requests.exceptions.JSONDecodeError, ValueError) as exc:
        return failure(f"{DISPLAY_NAME} search returned malformed data: {exc}")
    # 404 is a RequestException: catch it first, or a missing artwork_type
    # reads as a network failure.
    except requests.exceptions.HTTPError as exc:
        
        if exc.response.status_code == 404:
            return failure(f"{DISPLAY_NAME} search returned no results.")
        
        return failure(f"{DISPLAY_NAME} search request failed: {exc}")
    
    except requests.exceptions.RequestException as exc:
        return failure(f"{DISPLAY_NAME} search request failed: {exc}")

    artworks = payload.get("data") if isinstance(payload, dict) else None
    
    if not isinstance(artworks, list):
        return failure(f"{DISPLAY_NAME} search returned malformed data: no 'data' list.")

    return {
        "source": SOURCE,
        "query": query,
        "results": [_parse_artwork(a) for a in artworks if isinstance(a, dict)],
    }


## For testing  only ##
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.tools.cleveland_museum_search <query>")
        raise SystemExit(1)

    print(json.dumps(cleveland_search(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
