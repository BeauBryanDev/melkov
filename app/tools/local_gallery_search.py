
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Final

DB_PATH: Final[Path] = Path(__file__).parent.parent.parent / "melkov_gallery.db"
DEFAULT_LIMIT: Final[int] = 3

# Movements that span more than the display style of the same name. Keys are
# lower-case queries; values are extra display styles to include.
STYLE_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "post-impressionism": ("Pointillism",),
    "neo-impressionism": ("Pointillism",),
    "colour field": ("Color Field Painting",),
}

_COLUMNS: Final[str] = "id, artist, display_style, caption, width, height, s3_key"

# Search Melkov's own gallery (``melkov_gallery.db``) by style or artist.

# Reads the catalogue of the 22,258 images the VLM was fine-tuned on, in
# read-only mode. This is Melkov's own-catalog fallback - offered only after
# external museum searches fails or come back weak or empty, 
# # and the VLM Space is warmed up.

def _get_connection() -> sqlite3.Connection:
    """Open the gallery database in read-only mode.

    The backend never writes to this file - it was built once, offline, and
    copied to the server. Opening with mode=ro makes that guarantee explicit
    at the connection level, not just by convention.
    """
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _row_to_result(row: tuple[Any, ...]) -> dict[str, Any]:
    
    artwork_id, artist, display_style, caption, width, height, s3_key = row
    
    return {
        "id": artwork_id,
        "artist": artist,
        "style": display_style,
        "caption": caption,
        "width": width,
        "height": height,
        "s3_key": s3_key,
    }


def _normalise(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").split())


def resolve_styles(query: str, 
                   known_styles: list[str]
                   ) -> list[str]:
    """Map a free-text style query onto the catalogue's display styles.

    Matching is case-insensitive and tolerant of spaces/hyphens/underscores.
    An exact name wins; otherwise every display style containing the query
    as whole words matches ("renaissance" -> three styles). Aliases add
    related styles on top.

    Args:
        query: The style the user or model asked for.
        known_styles: The distinct ``display_style`` values in the database.

    Returns:
        Matching display styles, sorted; empty if nothing matches.
    """
    wanted = _normalise(query)
    loose = wanted.replace("-", " ")
    by_key = {_normalise(style): style for style in known_styles}

    matches: set[str] = set()
    
    if wanted in by_key:
        matches.add(by_key[wanted])
        
    else:
        for key, style in by_key.items():
            
            if f" {loose} " in f" {key.replace('-', ' ')} ":
                matches.add(style)

    for key, extra in STYLE_ALIASES.items():
        
        if key.replace("-", " ") == loose:
            matches.update(s for s in extra if s in known_styles)
            
    return sorted(matches)


def _envelope(query_type: str, 
              query: str, 
              **extra: Any # noqa: ARG002
              ) -> dict[str, Any]:
    
    return {
        "source": "local_gallery",
        "query_type": query_type,
        "query": query,
        **extra
        }
    

def search_by_style(style: str,
                    limit: int = DEFAULT_LIMIT
                    ) -> dict[str, Any]:
    """Look up gallery artworks by art style/movement.

    Args:
        style: A full style name ("Post-Impressionism", "Baroque") or a
            broader movement ("Renaissance"); see ``resolve_styles``.
        limit: Maximum number of results to return.

    Returns:
        {"source": "local_gallery", "query_type": "style", "query": ...,
        "styles": [matched display styles], "results": [{"id", "artist",
        "style", "caption", "width", "height", "s3_key"}, ...]}.
        
    A technical failure (DB missing/locked) adds an "error" field;
    a genuine empty match is just an empty list.
    """
    try:
        connection = _get_connection()
        try:
            cursor = connection.cursor()
            known = [row[0] for row in cursor.execute(
                "SELECT DISTINCT display_style FROM artworks"
            )]
            styles = resolve_styles(style, known)
            rows: list[tuple[Any, ...]] = []
            
            if styles:
                placeholders = ", ".join("?" for _ in styles)
                rows = cursor.execute(
                    f"SELECT {_COLUMNS} FROM artworks "
                    f"WHERE display_style IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
                    (*styles, limit),
                ).fetchall()
                
        finally:
            connection.close()
            
        return _envelope("style", style, styles=styles,
                         results=[_row_to_result(row) for row in rows])

    except sqlite3.Error as exc:
        return _envelope("style", style, styles=[], results=[],
                         error=f"Local gallery database error: {exc}")


def search_by_artist(artist_name: str, 
                     limit: int = DEFAULT_LIMIT
                     ) -> dict[str, Any]:
    """Look up gallery artworks by artist name (partial match).

    Uses a LIKE match rather than exact equality - the manifest's artist
    field is a full name (e.g. "Claude Monet"), so "Monet" still finds it.

    Args:
        artist_name: Full or partial artist name.
        limit: Maximum number of results to return.

    Returns:
        Same shape as  search_by_style  (without  styles ), with
         "query_type": "artist" .
    """
    try:
        connection = _get_connection()
        try:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM artworks "
                "WHERE artist LIKE ? ORDER BY RANDOM() LIMIT ?",
                (f"%{artist_name}%", limit),
            ).fetchall()
            
        finally:
            connection.close()
            
        return _envelope("artist", artist_name,
                         results=[_row_to_result(row) for row in rows])

    except sqlite3.Error as exc:
        return _envelope("artist", 
                         artist_name, 
                         results=[],
                         error=f"Local gallery database error: {exc}"
                         )
