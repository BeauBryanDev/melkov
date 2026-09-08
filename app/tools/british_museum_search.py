
from __future__ import annotations

from typing import Any, Final

from app.config import MUSEUM_SEARCH_LIMIT
from app.tools.wikidata_museum import Museum, search_museum

BRITISH_MUSEUM: Final[Museum] = Museum(
    qid="Q6373", 
    source="british_museum",
    display_name="British Museum"
)

# British Museum search over Wikidata.

def british_museum_search(query: str, 
                          limit: int = MUSEUM_SEARCH_LIMIT
                          ) -> dict[str, Any]:
    """Search British Museum works by title or artist."""
    
    return search_museum(BRITISH_MUSEUM, query, limit)


# For testing only ##
if __name__ == "__main__":
    
    import json
    import sys

    if len(sys.argv) < 2:
        
        print("Usage: python -m app.tools.british_museum_search <query>")
        
        raise SystemExit(1)
    
    print(json.dumps(british_museum_search(" ".join(sys.argv[1:])), 
                     ensure_ascii=False, 
                     indent=2))
