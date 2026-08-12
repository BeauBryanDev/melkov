from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import MET_API_BASE


logger = logging.getLogger(__name__)


#SETTINGS 
DEFAULT_TIMEOUT = 15
DEFAULT_MAX_RESULTS = 6
MAX_ALLOWED_RESULTS = 12

USER_AGENT = "Melkov/1.0 (Aegis-Art-Atelier)"

RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


# HTTP client

def _create_session() -> requests.Session:
    """
    Create a reusable HTTP session configured for reliable API requests.

    The session automatically retries transient HTTP failures such as
    rate limiting and temporary server errors.

    Returns:
        Configured requests.Session instance.
    """
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=4,
        pool_maxsize=4,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
    )

    return session


_SESSION = _create_session()


# Helpers

def _clean_string(value: Any) -> str | None:
    """
    Convert an API value into a normalized non-empty string.

    Args:
        value: Arbitrary API value.

    Returns:
        Cleaned string or None when the value is empty.
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    return value or None


def _extract_tags(raw_tags: Any) -> list[str]:
    """
    Extract human-readable tag terms from The Met tag objects.

    The Met returns tags in a structure similar to:

        [
            {
                "term": "Abstraction",
                "AAT_URL": "...",
                "Wikidata_URL": "..."
            }
        ]

    Args:
        raw_tags: Raw `tags` value returned by the API.

    Returns:
        List of normalized tag names.
    """
    if not isinstance(raw_tags, list):
        return []

    tags: list[str] = []

    for tag in raw_tags:
        if not isinstance(tag, dict):
            continue

        term = _clean_string(tag.get("term"))

        if term and term not in tags:
            tags.append(term)

    return tags


def _clamp_max_results(max_results: int) -> int:
    """
    Clamp the requested result count to a safe application limit.

    Args:
        max_results: Requested number of artworks.

    Returns:
        Safe result count between 1 and MAX_ALLOWED_RESULTS.
    """
    try:
        value = int(max_results)
        
    except (TypeError, ValueError):
        value = DEFAULT_MAX_RESULTS

    return max(1, min(value, MAX_ALLOWED_RESULTS))


# API requests

def _search_object_ids(
    query: str,
    *,
    title_only: bool = False,
    tags_only: bool = False,
    artist_or_culture: bool = False,
    medium: str | None = None,
    department_id: int | None = None,
    is_highlight: bool | None = None,
    is_on_view: bool | None = None,
    geo_location: str | None = None,
    date_begin: int | None = None,
    date_end: int | None = None,
) -> list[int]:
    """
    Search The Met API and return matching object IDs.

    Args:
        query: Search query.
        title_only: Search specifically within artwork titles.
        tags_only: Search specifically within subject tags.
        artist_or_culture: Search artist or culture fields.
        medium: Medium or object type filter.
        department_id: The Met department ID.
        is_highlight: Restrict to highlighted works.
        is_on_view: Restrict to works currently on view.
        geo_location: Geographic filter.
        date_begin: Beginning year for date filtering.
        date_end: Ending year for date filtering.

    Returns:
        List of matching object IDs.

    Raises:
        requests.RequestException:
            If the API request fails.
        ValueError:
            If date filtering is incomplete.
    """
    query = query.strip()

    if not query:
        raise ValueError("The Met search query cannot be empty.")

    if (date_begin is None) != (date_end is None):
        raise ValueError(
            "date_begin and date_end must be provided together."
        )

    params: dict[str, Any] = {
        "q": query,
        "hasImages": "true",
    }

    if title_only:
        params["title"] = "true"

    if tags_only:
        params["tags"] = "true"

    if artist_or_culture:
        params["artistOrCulture"] = "true"

    if medium:
        params["medium"] = medium

    if department_id is not None:
        params["departmentId"] = int(department_id)

    if is_highlight is not None:
        params["isHighlight"] = str(is_highlight).lower()

    if is_on_view is not None:
        params["isOnView"] = str(is_on_view).lower()

    if geo_location:
        params["geoLocation"] = geo_location

    if date_begin is not None and date_end is not None:
        params["dateBegin"] = int(date_begin)
        params["dateEnd"] = int(date_end)

    logger.info(
        "Searching The Met collection: query=%r params=%s",
        query,
        params,
    )

    response = _SESSION.get(
        f"{MET_API_BASE}/search",
        params=params,
        timeout=DEFAULT_TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    object_ids = payload.get("objectIDs") or []

    logger.info(
        "The Met search returned %d object IDs.",
        len(object_ids),
    )

    return [int(object_id) for object_id in object_ids if object_id is not None]


def _get_object(object_id: int) -> dict[str, Any] | None:
    """
    Retrieve a single artwork record from The Met.

    Args:
        object_id: The Met unique object ID.

    Returns:
        Raw artwork dictionary or None if unavailable.
    """
    try:
        response = _SESSION.get(
            f"{MET_API_BASE}/objects/{object_id}",
            timeout=DEFAULT_TIMEOUT,
        )

        if not response.ok:
            logger.warning(
                "The Met object request failed: object_id=%s status=%s",
                object_id,
                response.status_code,
            )
            return None

        payload = response.json()

        if not isinstance(payload, dict):
            logger.warning(
                "Unexpected object response for object_id=%s",
                object_id,
            )
            return None

        return payload

    except requests.RequestException:
        logger.exception(
            "Failed to retrieve The Met object %s.",
            object_id,
        )
        return None


# Metadata normalization

def _normalize_artwork(
    obj: dict[str, Any],
    *,
    require_public_domain: bool = True,
) -> dict[str, Any] | None:
    """
    Convert a raw The Met object into a compact application-level record.

    The normalized structure intentionally contains only information useful
    to Melkov, GPT-4o, and the frontend. This prevents the orchestrator from
    receiving the large raw JSON object returned by The Met.

    Args:
        obj: Raw artwork object from The Met.
        require_public_domain: When True, only return public-domain works.

    Returns:
        Normalized artwork dictionary, or None when the artwork should be
        excluded.
    """
    object_id = obj.get("objectID")

    if object_id is None:
        return None

    primary_image = _clean_string(obj.get("primaryImage"))

    if not primary_image:
        return None

    is_public_domain = bool(obj.get("isPublicDomain", False))

    if require_public_domain and not is_public_domain:
        return None

    artist_name = _clean_string(obj.get("artistDisplayName"))

    artist_bio = _clean_string(obj.get("artistDisplayBio"))

    artist_nationality = _clean_string(
        obj.get("artistNationality")
    )

    artist_begin_date = obj.get("artistBeginDate")
    artist_end_date = obj.get("artistEndDate")

    artist_dates = None

    if artist_begin_date or artist_end_date:
        artist_dates = {
            "begin": artist_begin_date,
            "end": artist_end_date,
        }

    return {
        "object_id": object_id,
        "title": _clean_string(obj.get("title")),
        "artist": artist_name,
        "artist_role": _clean_string(obj.get("artistRole")),
        "artist_prefix": _clean_string(obj.get("artistPrefix")),
        "artist_bio": artist_bio,
        "artist_nationality": artist_nationality,
        "artist_dates": artist_dates,
        "date": _clean_string(obj.get("objectDate")),
        "date_begin": obj.get("objectBeginDate"),
        "date_end": obj.get("objectEndDate"),
        "medium": _clean_string(obj.get("medium")),
        "dimensions": _clean_string(obj.get("dimensions")),
        "culture": _clean_string(obj.get("culture")),
        "period": _clean_string(obj.get("period")),
        "dynasty": _clean_string(obj.get("dynasty")),
        "reign": _clean_string(obj.get("reign")),
        "classification": _clean_string(obj.get("classification")),
        "department": _clean_string(obj.get("department")),
        "object_name": _clean_string(obj.get("objectName")),
        "country": _clean_string(obj.get("country")),
        "city": _clean_string(obj.get("city")),
        "region": _clean_string(obj.get("region")),
        "tags": _extract_tags(obj.get("tags")),
        "is_highlight": bool(obj.get("isHighlight", False)),
        "is_on_view": bool(obj.get("isOnView", False)),
        "is_public_domain": is_public_domain,
        "image_url": primary_image,
        "image_url_small": _clean_string(
            obj.get("primaryImageSmall")
        ),
        "additional_images": [
            image
            for image in (obj.get("additionalImages") or [])
            if isinstance(image, str) and image.strip()
        ],
        "object_url": _clean_string(
            obj.get("objectURL") or obj.get("linkResource")
        ),
        "credit_line": _clean_string(obj.get("creditLine")),
        "repository": _clean_string(obj.get("repository")),
        "object_wikidata_url": _clean_string(
            obj.get("objectWikidata_URL")
        ),
        "artist_wikidata_url": _clean_string(
            obj.get("artistWikidata_URL")
        ),
        "artist_ulan_url": _clean_string(
            obj.get("artistULAN_URL")
        ),
    }


# Public tool

def search_met_artworks(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    *,
    artist_or_culture: bool = False,
    medium: str | None = None,
    department_id: int | None = None,
    is_highlight: bool | None = None,
    is_on_view: bool | None = None,
    title_only: bool = False,
    tags_only: bool = False,
    geo_location: str | None = None,
    date_begin: int | None = None,
    date_end: int | None = None,
    require_public_domain: bool = True,
) -> list[dict[str, Any]]:
    """
    Search The Metropolitan Museum of Art collection.

    This is the main tool function intended to be exposed to the
    GPT-4o orchestrator.

    Args:
        query:
            Natural-language search query such as "Claude Monet",
            "Impressionism", "Water Lilies", or "Paris landscapes".

        max_results:
            Maximum number of normalized artworks to return. The application
            limits this to MAX_ALLOWED_RESULTS.

        artist_or_culture:
            Restrict the Met search to artist name or culture fields.

        medium:
            Restrict results by medium/object type. Examples include
            "Paintings", "Sculpture", "Drawings", or "Photographs".

        department_id:
            The Met department identifier. European Paintings is department
            11.

        is_highlight:
            Restrict results to The Met's highlighted works.

        is_on_view:
            Restrict results to works currently on view.

        title_only:
            Restrict the query to artwork titles.

        tags_only:
            Restrict the query to subject keyword tags.

        geo_location:
            Geographic filter such as "France", "Paris", or "Europe".

        date_begin:
            Beginning year for date filtering.

        date_end:
            Ending year for date filtering.

        require_public_domain:
            When True, return only works explicitly marked as public domain
            by The Met. This is the default because Melkov's frontend may
            display artwork images.

    Returns:
        A list of normalized artwork records suitable for the agent and
        frontend.

    Raises:
        ValueError:
            If the query is empty or date filters are invalid.
        requests.RequestException:
            If the initial search request fails.
    """
    limit = _clamp_max_results(max_results)

    object_ids = _search_object_ids(
        query,
        title_only=title_only,
        tags_only=tags_only,
        artist_or_culture=artist_or_culture,
        medium=medium,
        department_id=department_id,
        is_highlight=is_highlight,
        is_on_view=is_on_view,
        geo_location=geo_location,
        date_begin=date_begin,
        date_end=date_end,
    )

    if not object_ids:
        return []

    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    # The Met search endpoint returns IDs, while detailed artwork metadata
    # requires one request per object. We intentionally keep this sequential
    # for a small portfolio-agent workload and to remain comfortably below
    # The Met's published request-rate limit.
    for object_id in object_ids:
        if len(results) >= limit:
            break

        if object_id in seen_ids:
            continue

        seen_ids.add(object_id)

        obj = _get_object(object_id)

        if obj is None:
            continue

        artwork = _normalize_artwork(
            obj,
            require_public_domain=require_public_domain,
        )

        if artwork is None:
            continue

        results.append(artwork)

    logger.info(
        "The Met tool returned %d artworks for query=%r.",
        len(results),
        query,
    )

    return results