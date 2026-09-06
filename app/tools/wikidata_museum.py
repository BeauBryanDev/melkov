
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import requests

from app.config import (
    WIKIDATA_SPARQL_ENDPOINT,
    WIKIDATA_TIMEOUT,
    WIKIDATA_USER_AGENT,
    MUSEUM_SEARCH_LIMIT,
)

MAX_LIMIT: Final[int] = 20

# Shared Louvre/British Museum search via the Wikidata SPARQL endpoint

@dataclass(frozen=True, slots=True)
class Museum:
    """A museum reachable through Wikidata's P195 collection property."""

    qid: str
    source: str
    display_name: str


def build_sparql_query(museum: Museum, query_text: str, limit: int) -> str:
    """SPARQL matching the title or the creator's label against query_text."""
    safe_query = query_text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    # P195/P361*: works usually link to a department that is part of the museum.
    # GROUP BY collapses one row per creator/image/url into one per work.
    return f"""
    SELECT ?item (SAMPLE(?label) AS ?itemLabel) (SAMPLE(?creatorLabel) AS ?creatorLabel)
           (SAMPLE(?img) AS ?image) (SAMPLE(?date) AS ?inception)
           (SAMPLE(?url) AS ?describedAtUrl) WHERE {{
      ?item wdt:P195/wdt:P361* wd:{museum.qid} .
      ?item rdfs:label ?label .
      FILTER(LANG(?label) = "en")
      OPTIONAL {{
        ?item wdt:P170 ?creator .
        ?creator rdfs:label ?creatorLabel .
        FILTER(LANG(?creatorLabel) = "en")
      }}
      OPTIONAL {{ ?item wdt:P18 ?img . }}
      OPTIONAL {{ ?item wdt:P571 ?date . }}
      OPTIONAL {{ ?item wdt:P973 ?url . }}
      FILTER(
        CONTAINS(LCASE(?label), LCASE("{safe_query}"))
        || CONTAINS(LCASE(?creatorLabel), LCASE("{safe_query}"))
      )
    }}
    GROUP BY ?item
    LIMIT {limit}
    """


def parse_bindings(museum: Museum, bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw SPARQL JSON bindings into the shared museum-result shape."""
    results: list[dict[str, Any]] = []
    for row in bindings:
        # P973 is optional; the Wikidata entity page is always a working link.
        object_url = (
            row.get("describedAtUrl", {}).get("value")
            or row.get("item", {}).get("value")
        )
        results.append(
            {
                "title": row.get("itemLabel", {}).get("value"),
                "artist": row.get("creatorLabel", {}).get("value"),
                "date": row.get("inception", {}).get("value"),
                "image_url": row.get("image", {}).get("value"),
                "object_url": object_url,
                "museum": f"{museum.display_name} (via Wikidata)",
            }
        )
    return results


def search_museum(museum: Museum, 
                  query: str, 
                  limit: int = MUSEUM_SEARCH_LIMIT
                  ) -> dict[str, Any]:
    """Search one museum. Returns {source, query, results, [error]}; never raises."""
    limit = max(1, 
                min(int(limit), 
                MAX_LIMIT))
    
    envelope: dict[str, Any] = {"source": museum.source, 
                                "query": query, "results": []
                                }
    headers = {"User-Agent": WIKIDATA_USER_AGENT, 
               "Accept": "application/sparql-results+json"
               }
    params = {"query": build_sparql_query(museum, query, limit), 
              "format": "json"
              }

    try:
        response = requests.get(
            WIKIDATA_SPARQL_ENDPOINT,
            params=params, 
            headers=headers, 
            timeout=WIKIDATA_TIMEOUT
        )
        response.raise_for_status()
        
        bindings = response.json().get("results", {}).get("bindings", [])
        
        envelope["results"] = parse_bindings(museum, bindings)
        
    except requests.exceptions.Timeout:
        envelope["error"] = f"{museum.display_name} search (Wikidata) timed out."
        
    except requests.exceptions.JSONDecodeError as exc:
        envelope["error"] = f"{museum.display_name} search (Wikidata) returned malformed data: {exc}"
        
    except requests.exceptions.RequestException as exc:
        envelope["error"] = f"{museum.display_name} search (Wikidata) request failed: {exc}"
        
    except (ValueError, KeyError, AttributeError) as exc:
        envelope["error"] = f"{museum.display_name} search (Wikidata) returned malformed data: {exc}"
        
    return envelope
