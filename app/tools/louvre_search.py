"""Louvre Museum search over Wikidata."""

from __future__ import annotations

from typing import Any, Final

from app.config import MUSEUM_SEARCH_LIMIT
from app.tools.wikidata_museum import Museum, search_museum

LOUVRE: Final[Museum] = Museum(qid="Q19675", 
                               source="louvre", 
                               display_name="Louvre Museum"
                               )


def louvre_search(query: str, 
                  limit: int = MUSEUM_SEARCH_LIMIT
                  ) -> dict[str, Any]:
    """Search Louvre Museum works by title or artist."""
    return search_museum(LOUVRE, 
                         query, 
                         limit)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.tools.louvre_search <query>")
        raise SystemExit(1)
    
    print(json.dumps(louvre_search(" ".join(sys.argv[1:])), ensure_ascii=False, indent=2))
