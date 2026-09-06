"""Painting-technique videos from trusted YouTube channels."""

from __future__ import annotations

import logging
from typing import Any, Final

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import YOUTUBE_DATA_API_KEY, YOUTUBE_MAX_RESULTS, YOUTUBE_SEARCH_POOL

logger = logging.getLogger(__name__)

# Matched by case-insensitive prefix: real titles carry suffixes ("Marco Bucci Art").
TRUSTED_CHANNELS: Final[tuple[str, ...]] = (
    "Marco Bucci",
    "James Gurney",
    "Proko",
    "Andrew Tischler",
    "Sinix Design",
)
DESCRIPTION_CHARS: Final[int] = 120


def _is_trusted(channel_title: str) -> bool:
    
    title = channel_title.strip().lower()
    
    return any(title.startswith(name.lower()) for name in TRUSTED_CHANNELS)


def get_art_advice(query: str) -> list[dict[str, Any]]:
    """Return up to YOUTUBE_MAX_RESULTS videos; empty if none. Raises RuntimeError on API/key failure."""
    if not YOUTUBE_DATA_API_KEY:
        raise RuntimeError("YOUTUBE_DATA_API_KEY is not set")

    # Channel names ride inside the query: one request, 100 quota units.
    channels_query = " OR ".join(f'"{channel}"' for channel in TRUSTED_CHANNELS)
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_DATA_API_KEY)
        response = (
            youtube.search()
            .list(
                q=f"{query} ({channels_query})",
                part="snippet",
                type="video",
                videoEmbeddable="true",
                maxResults=YOUTUBE_SEARCH_POOL,
            )
            .execute()
        )
    except HttpError as error:
        raise RuntimeError(f"YouTube Data API error: {error}") from error

    results: list[dict[str, Any]] = []
    
    for item in response.get("items", []):
        
        snippet = item.get("snippet", {})
        channel = snippet.get("channelTitle", "")
        video_id = item.get("id", {}).get("videoId")
        
        if not video_id or not _is_trusted(channel):
            continue
        
        description = snippet.get("description", "")
        
        if len(description) > DESCRIPTION_CHARS:
            
            description = description[:DESCRIPTION_CHARS] + "..."
            
        results.append(
            {
                "title": snippet.get("title", "Untitled"),
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description_snippet": description,
            }
        )
        if len(results) >= YOUTUBE_MAX_RESULTS:
            break
        
    return results



## Only for testing ##
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.tools.artist_advisor <query>")
        raise SystemExit(1)
    
    print(json.dumps(get_art_advice(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
