"""Phase 3: chunk the extracted books into retrieval units.

Chapters are detected from the extracted text using each book's own
heading conventions (numbered chapters, roman numerals, or all-caps
display heads). Long chapters are split into overlapping paragraph
groups so an argument spanning a paragraph boundary is not orphaned.

Historically-organised books get a ``periodo_arte`` tag derived from
their chapter heading; topical books leave it null.

Output: ``RAG/chunks.jsonl``, one JSON object per chunk, matching the
metadata schema in ``RAG_Instructions.md`` §7. This file is the input to
the Colab embedding/ingestion step.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final, Iterator

from corpus import CORPUS, EXTRACT_DIR, Book
from extract import HEADING_MARK

CHUNKS_PATH: Final[Path] = Path(__file__).resolve().parent / "chunks.jsonl"

#: Target chunk size in words; chapters longer than this are subdivided.
MAX_CHUNK_WORDS: Final[int] = 900
#: Words of overlap carried between consecutive chunks of a chapter.
OVERLAP_WORDS: Final[int] = 80
#: Chunks shorter than this are dropped as extraction residue.
MIN_CHUNK_WORDS: Final[int] = 40

#: Articles/prepositions that stay lowercase in a title-cased heading and
#: so must not count against it.
_MINOR_WORDS: Final[frozenset[str]] = frozenset(
    "a an the of and or in on to for from with by as at is its".split()
)

#: OCR word-splits seen in chapter headings during the first full run.
#: Verified against real output before being added, not guessed.
_OCR_SPLIT_FIXES: Final[dict[str, str]] = {
    "PHY SICS": "PHYSICS",
    "LI ST": "LIST",
    "PSHCHOLOGICAL": "PSYCHOLOGICAL",
}

#: Chapter heading forms across the corpus: "CHAPTER IV", "IV. Egypt",
#: "3.2 Visual Weight", or a short all-caps display line.
_HEADING_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^(?:CHAPTER|Chapter)\s+([IVXLC]+|\d+)\b\.?\s*(.*)$"),
    re.compile(r"^([IVXLC]{1,6})\.\s+([A-Z][A-Za-z' -]{2,60})$"),
    re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\s+([A-Z][A-Za-z' -]{2,60})$"),
    re.compile(r"^([A-Z][A-Z ',-]{6,50})$"),
)

#: Period/movement keywords searched in chapter headings and opening text
#: of chronological books. Order matters: earlier entries win ties.
_PERIOD_KEYWORDS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Prehistoric", ("before history", "prehistor", "cave")),
    ("Ancient Egypt", ("egypt", "pharaoh")),
    ("Ancient Near East", ("ancient orient", "mesopotam", "assyr", "babylon", "persia")),
    ("Classical Antiquity", ("greece", "greek", "hellen", "rome", "roman", "classical")),
    ("Early Christian & Byzantine", ("byzan", "early christian", "christendom")),
    ("Islamic Art", ("islam", "muslim", "moorish")),
    ("Medieval", ("middle ages", "medieval", "romanesque", "gothic", "cathedral")),
    ("Renaissance", ("renaissance", "quattrocento", "cinquecento", "florence")),
    ("Baroque", ("baroque", "seventeenth century", "counter-reformation")),
    ("Rococo & 18th Century", ("rococo", "eighteenth century")),
    ("Neoclassicism & Romanticism", ("neoclassic", "romantic", "revolution")),
    ("Impressionism", ("impressionis",)),
    ("Modern", ("modern", "twentieth century", "abstract", "cubis", "expressionis")),
)


@dataclass(slots=True)
class Chapter:
    """A chapter accumulated as words paired with their source pages.

    Attributes:
        heading: The chapter heading, or None for pre-heading front matter.
        words: The chapter's words in document order.
        pages: The page each word came from, aligned with ``words``.
    """

    heading: str | None
    words: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)


@dataclass(slots=True)
class Chunk:
    """A single retrieval unit, matching the RAG metadata schema.

    Attributes:
        text: The chunk's body text.
        book_title: Verified title of the source book.
        author: Verified author of the source book.
        book_id: Stable book identifier for metadata filtering.
        chunk_type: Always ``narrative``; figures are not ingested.
        capitulo: Chapter/section heading, or None if undetected.
        periodo_arte: Art-historical period, or None for topical chapters.
        subtopic: Thematic tag, or None.
        pagina_aprox: Page on which the chunk's text starts.
        pagina_fin: Page on which it ends; equal to ``pagina_aprox`` when
            the chunk sits entirely on one page.
        chunk_id: Unique identifier within the corpus.
    """

    text: str
    book_title: str
    author: str
    book_id: str
    chunk_type: str
    capitulo: str | None
    periodo_arte: str | None
    subtopic: str | None
    pagina_aprox: int | None
    pagina_fin: int | None
    chunk_id: str


def _repair_ocr_splits(text: str) -> str:
    """Repair OCR word-splits observed in the corpus's headings.

    Built from actual extraction output rather than guessed in advance,
    per ``RAG_Instructions.md`` §5: these are the splits that survived
    into chapter labels in the first full run.

    Args:
        text: A candidate heading.

    Returns:
        The heading with known splits rejoined.
    """
    for broken, fixed in _OCR_SPLIT_FIXES.items():
        text = text.replace(broken, fixed)
    return text


def _is_plausible_heading(text: str) -> bool:
    """Judge whether a candidate heading is a real chapter head.

    Applied to every candidate, however it was matched, so that OCR
    debris cannot reach a user-visible citation.

    Args:
        text: The candidate heading.

    Returns:
        True when the text looks like a genuine heading.
    """
    # Drop any leading chapter number so numbering does not trip the
    # short-word check below ("II THE MOVEMENT OF THE TRIANGLE").
    body = re.sub(r"^(?:[IVXLC]{1,6}|\d{1,2}(?:\.\d{1,2})*)[.\s]+", "", text).strip()
    words = body.split()
    if not words:
        return False
    letters = sum(c.isalpha() for c in body)
    if letters < 4 or letters / len(body) < 0.5:
        return False
    # Scanner artifacts pass the letter test while carrying no word at all
    # ("OOQOOOOOOOOOOOO"): real headings use a variety of letters and do
    # not repeat one character run after run.
    alpha = [c.lower() for c in body if c.isalpha()]
    if len(set(alpha)) < 4 or re.search(r"(.)\1{3,}", body, re.IGNORECASE):
        return False
    # Figure and plate references are captions, not chapters.
    if re.match(r"^(?:FIGURE|Figure|PLATE|Plate)\b", body):
        return False
    significant = [w for w in words if w.lower() not in _MINOR_WORDS]
    if not significant:
        return False
    return all(len(w.strip(".,'-")) >= 3 for w in significant)


def _match_heading(line: str) -> str | None:
    """Return the heading text if a line is a chapter heading.

    Headings are marked during extraction from font-size metadata. A
    marked line still has to look like a chapter head — running display
    type and drop-cap fragments are marked too — so numbering patterns
    and casing are used as a second filter.

    Args:
        line: A single line of extracted text.

    Returns:
        The normalized heading, or None if the line is body text.
    """
    if not line.startswith(HEADING_MARK):
        return None
    stripped = _repair_ocr_splits(line[len(HEADING_MARK) :].strip())
    for pattern in _HEADING_PATTERNS:
        if (match := pattern.match(stripped)) is not None:
            candidate = " ".join(part for part in match.groups() if part).strip()
            # Numbered and all-caps forms still have to survive the quality
            # gate — the all-caps pattern happily matches OCR debris.
            return candidate if _is_plausible_heading(candidate) else None
    # Marked but unnumbered: accept only display-cased multi-word heads
    # (Itten's and Arnheim's). This rejects drop-cap fragments ("THIS",
    # "WHEN,") and prose lines the size heuristic marked by mistake.
    words = stripped.split()
    if not (2 <= len(words) <= 9) or stripped.endswith((".", ",", ";", ":")):
        return None
    # A sentence boundary inside the line means we caught running prose,
    # not a heading ("of the Nativity. We").
    if re.search(r"[.!?]\s", stripped):
        return None
    # A real heading opens on a significant word. Leading "of"/"the" means
    # the line is the tail of a caption or sentence ("of Adam", "of Max").
    if words[0].lower() in _MINOR_WORDS:
        return None
    if not _is_plausible_heading(stripped):
        return None
    significant = [w for w in words if w.lower() not in _MINOR_WORDS]
    if all(w.isupper() for w in significant) or all(
        w[:1].isupper() for w in significant
    ):
        return stripped
    return None


def _detect_period(text: str) -> str | None:
    """Infer the art-historical period a passage covers.

    Args:
        text: Chapter heading plus its opening text.

    Returns:
        The matched period label, or None when nothing matches.
    """
    lowered = text.lower()
    for period, keywords in _PERIOD_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return period
    return None


def _split_paragraphs(length: int) -> Iterator[tuple[int, int]]:
    """Yield overlapping ``(start, end)`` word offsets for a chapter.

    Offsets rather than word lists, so the caller can map a window back to
    the page it starts on.

    Args:
        length: Total number of words in the chapter.

    Yields:
        Half-open index ranges of at most ``MAX_CHUNK_WORDS`` words,
        overlapping by ``OVERLAP_WORDS``.
    """
    step = MAX_CHUNK_WORDS - OVERLAP_WORDS
    for start in range(0, length, step):
        end = min(start + MAX_CHUNK_WORDS, length)
        if end > start:
            yield start, end
        if start + MAX_CHUNK_WORDS >= length:
            break


def chunk_book(book: Book) -> list[Chunk]:
    """Chunk one extracted book.

    Args:
        book: The corpus entry, used for metadata and tagging rules.

    Returns:
        The book's chunks in document order.
    """
    record = json.loads((EXTRACT_DIR / f"{book.book_id}.json").read_text())

    # Accumulate each chapter as a flat word list with the page each word
    # came from, so a chunk can cite the page it actually starts on rather
    # than the page its chapter opened on.
    chapters: list[Chapter] = [Chapter(heading=None)]
    for page in record["pages"]:
        page_number = int(page["number"])
        for line in page["text"].split("\n"):
            if not line.strip():
                continue
            heading = _match_heading(line)
            if heading is not None:
                chapters.append(Chapter(heading=heading))
                continue
            # A marked line that is not a chapter head (a display
            # quotation, a drop cap) stays as body text, minus its mark.
            words = line.lstrip(HEADING_MARK).strip().split()
            chapters[-1].words.extend(words)
            chapters[-1].pages.extend([page_number] * len(words))

    chunks: list[Chunk] = []
    for chapter in chapters:
        if not chapter.words:
            continue

        period = (
            _detect_period(f"{chapter.heading or ''} {' '.join(chapter.words[:120])}")
            if book.chronological
            else None
        )
        for start, end in _split_paragraphs(len(chapter.words)):
            window = chapter.words[start:end]
            if len(window) < MIN_CHUNK_WORDS:
                continue
            # Where the chapter heading was not recovered, fall back to the
            # chunk's own text so chronological books still carry a period.
            chunk_period = period
            if book.chronological and chunk_period is None:
                chunk_period = _detect_period(" ".join(window[:250]))
            chunks.append(
                Chunk(
                    text=" ".join(window),
                    book_title=book.title,
                    author=book.author,
                    book_id=book.book_id,
                    chunk_type="narrative",
                    capitulo=chapter.heading,
                    periodo_arte=chunk_period,
                    subtopic=book.subtopic,
                    pagina_aprox=chapter.pages[start],
                    pagina_fin=chapter.pages[end - 1],
                    chunk_id=f"{book.book_id}_{len(chunks):05d}",
                )
            )
    return chunks


def main() -> None:
    """Chunk every extracted book and write ``chunks.jsonl``."""
    all_chunks: list[Chunk] = []
    summary: list[tuple[str, int, int, int]] = []

    for book in CORPUS:
        chunks = chunk_book(book)
        all_chunks.extend(chunks)
        chapters = len({c.capitulo for c in chunks if c.capitulo})
        periods = len({c.periodo_arte for c in chunks if c.periodo_arte})
        summary.append((book.book_id, len(chunks), chapters, periods))

    with CHUNKS_PATH.open("w") as handle:
        for chunk in all_chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    header = f"{'book_id':<34}{'chunks':>8}{'chapters':>10}{'periods':>9}"
    print(header)
    print("-" * len(header))
    for book_id, n_chunks, chapters, periods in summary:
        print(f"{book_id:<34}{n_chunks:>8}{chapters:>10}{periods:>9}")
    print(f"\ntotal chunks: {len(all_chunks)}\nchunks -> {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
