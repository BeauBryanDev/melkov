"""Phase 1-2: extract and clean typed text from the corpus PDFs.

Extraction uses the PDF's native text layer only — no OCR. Images, plates,
charts and diagrams are ignored entirely; a page carrying no text layer
simply yields nothing and is recorded as skipped.

Cleaning removes the artifacts the Phase 0 audit found in this corpus:
running headers/footers, line-break hyphenation, letter-spaced display
type (``C O L D - W A R M``), Project Gutenberg boilerplate, and the
short numbered plate captions that sit beside figures.

Output is one JSON file per book under ``RAG/extracted/``, holding cleaned
page-level text ready for Phase 3 chunking.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Final

import pymupdf

from corpus import CORPUS, EXTRACT_DIR, Book

#: A line repeated on at least this fraction of pages is a running header
#: or footer rather than body text.
HEADER_PAGE_FRACTION: Final[float] = 0.10
#: Only the first/last few lines of a page are considered header/footer
#: candidates.
EDGE_LINES: Final[int] = 2
#: Lines longer than this are body text, never running heads.
MAX_HEADER_CHARS: Final[int] = 70
#: Pages with less text than this are treated as plate/blank pages.
MIN_PAGE_CHARS: Final[int] = 120

_PAGE_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"^[\divxlcIVXLC\s.\-—]+$")
#: Plate captions: "245. Caravaggio: Doubting Thomas. About 1600. Berlin"
#: (Gombrich, Arnheim) and "Plate XVIII" / "Fig. 38" openers.
_PLATE_CAPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:Plate\s+[IVXLC\d]+"
    r"|Fig(?:ure|s?\.)\s*\d+"
    r"|\d{1,3}\.\s+[A-Za-z][A-Za-z\s.'-]{2,30}:)"
)
#: Artist attribution lines in Itten's plate blocks:
#: "Jan van Eyck, 1390-1441;" — a name followed by a life-span.
_ARTIST_DATES_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z][A-Za-z.'\- ]{2,40},\s*\d{3,4}\s*[-–]\s*\d{3,4}\s*;?\s*$"
)
#: Lines that are mostly punctuation/symbol debris shed by figure regions
#: during extraction, e.g. "^p", "^' y", "•", "r'^^^*".
_JUNK_LINE_RE: Final[re.Pattern[str]] = re.compile(r"^[^A-Za-z0-9]*$")
#: Minimum share of letters/digits/spaces a line must have to be prose.
MIN_ALNUM_RATIO: Final[float] = 0.75
#: A line typeset at this multiple of the body font size is a heading.
#: Set well above OCR size jitter (Arnheim's body spans wobble 7.9-8.3
#: while its chapter heads sit near 19.5).
HEADING_SIZE_RATIO: Final[float] = 1.45
#: If a document's largest type is below this multiple of body size it is
#: a single-font export (Faure, Kandinsky) and size tells us nothing —
#: heading detection falls back to all-caps prefixes alone.
MIN_SIZE_SPREAD: Final[float] = 1.35
#: Headings are short; longer large-type lines are display quotations.
MAX_HEADING_CHARS: Final[int] = 70
#: Sentinel prefixing heading lines in the extracted text, so Phase 3 can
#: find chapter boundaries without re-guessing from the prose.
HEADING_MARK: Final[str] = "␟"


def _is_debris(line: str) -> bool:
    """Return True for symbol debris shed by figure regions.

    Args:
        line: A cleaned text line.

    Returns:
        True when the line is too short or too symbol-dense to be prose.
    """
    if _JUNK_LINE_RE.match(line) or len(line) <= 2:
        return True
    if len(line) > 40:
        return False
    good = sum(c.isalnum() or c.isspace() for c in line)
    return good / len(line) < MIN_ALNUM_RATIO
#: A line ending mid-sentence: no terminal punctuation, so the paragraph
#: continues on the next line and the two should be reflowed together.
_SENTENCE_END_RE: Final[re.Pattern[str]] = re.compile(r"[.!?:;\"')\]]$")
_GUTENBERG_START_RE: Final[re.Pattern[str]] = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.IGNORECASE
)
_GUTENBERG_END_RE: Final[re.Pattern[str]] = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG", re.IGNORECASE
)
#: Runs of single characters separated by spaces, i.e. letter-spaced display
#: type. Three characters is the useful floor — Itten's title page sets
#: "A N D" that way — and short enough runs of real initials are rare.
_LETTERSPACED_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:(?<=\s)|^)((?:[A-Za-z]\s){2,}[A-Za-z])(?=\s|$)"
)
_HYPHEN_BREAK_RE: Final[re.Pattern[str]] = re.compile(r"([A-Za-z])[-­]\s*\n\s*([a-z])")
#: A chapter head run in capitals, optionally roman-numbered, sitting at
#: the start of a line and followed by ordinary sentence-case prose:
#: "II. THE MOVEMENT OF THE TRIANGLE The life of the spirit may be ...".
_CAPS_HEADING_RE: Final[re.Pattern[str]] = re.compile(
    r"^((?:(?:CHAPTER\s+)?[IVXLC]{1,6}\.\s*)?"
    r"[A-Z][A-Z'’\-]*(?:\s+(?:[A-Z][A-Z'’\-]*|OF|AND|THE|IN|TO|A)){1,9})"
    r"(?:\s+(?=[A-Z][a-z])|\s*$)"
)


@dataclass(slots=True)
class Page:
    """One extracted page of body text.

    Attributes:
        number: 1-based page number as printed in the PDF's page order.
        text: Cleaned body text, headers and captions removed.
    """

    number: int
    text: str


def _normalize_unicode(text: str) -> str:
    """Fold ligatures and exotic spacing into plain ASCII-ish text.

    Args:
        text: Raw text from the PDF text layer.

    Returns:
        NFKC-normalized text with quotes and dashes regularised.
    """
    text = unicodedata.normalize("NFKC", text)
    for src, dst in (
        ("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
        (" ", " "), ("—", "—"), ("ﬁ", "fi"), ("ﬂ", "fl"),
    ):
        text = text.replace(src, dst)
    return text


def _fix_letterspacing(text: str) -> str:
    """Collapse letter-spaced display type back into words.

    Itten's chapter headings are typeset as ``C O L D - W A R M``; left as
    is they tokenize into meaningless single characters.

    Args:
        text: A line of text.

    Returns:
        The line with letter-spaced runs collapsed.
    """
    return _LETTERSPACED_RE.sub(lambda m: m.group(1).replace(" ", ""), text)


def _find_running_lines(pages: list[list[str]]) -> set[str]:
    """Identify running headers/footers by cross-page repetition.

    Args:
        pages: Per-page lists of raw text lines.

    Returns:
        The set of normalized line forms to strip from page edges.
    """
    counts: Counter[str] = Counter()
    for lines in pages:
        edge = lines[:EDGE_LINES] + lines[-EDGE_LINES:]
        for line in {l for l in edge if len(l) <= MAX_HEADER_CHARS}:
            # Digits vary page to page; compare the stable part.
            counts[re.sub(r"\d+", "#", line).strip().lower()] += 1
    threshold = max(3, int(len(pages) * HEADER_PAGE_FRACTION))
    return {form for form, n in counts.items() if n >= threshold and form}


def _strip_edges(lines: list[str], running: set[str]) -> list[str]:
    """Drop running heads, page numbers and plate captions from a page.

    Args:
        lines: The page's text lines.
        running: Normalized running-header forms for this book.

    Returns:
        The remaining body lines.
    """
    kept: list[str] = []
    for index, line in enumerate(lines):
        near_edge = index < EDGE_LINES or index >= len(lines) - EDGE_LINES
        form = re.sub(r"\d+", "#", line).strip().lower()
        if near_edge and (form in running or _PAGE_NUMBER_RE.match(line)):
            continue
        if _PLATE_CAPTION_RE.match(line) or _ARTIST_DATES_RE.match(line):
            continue
        if _is_debris(line):
            continue
        kept.append(line)
    return kept


def _body_font_size(doc: pymupdf.Document, sample_step: int) -> float:
    """Estimate the document's body-text font size.

    Uses the character-weighted most common span size, so occasional
    headings and captions cannot outvote running prose.

    Args:
        doc: An open PyMuPDF document.
        sample_step: Sample every Nth page rather than all of them.

    Returns:
        The body font size in points.
    """
    weights: Counter[float] = Counter()
    for index in range(0, doc.page_count, sample_step):
        data = doc[index].get_text("dict")
        for block in data.get("blocks", ()):
            for line in block.get("lines", ()):
                for span in line.get("spans", ()):
                    text = span.get("text", "").strip()
                    if text:
                        weights[round(float(span["size"]), 1)] += len(text)
    return weights.most_common(1)[0][0] if weights else 10.0


def _heading_threshold(doc: pymupdf.Document, body_size: float, step: int) -> float | None:
    """Decide the font size above which a line counts as a heading.

    Args:
        doc: An open PyMuPDF document.
        body_size: The document's body font size.
        step: Page sampling step.

    Returns:
        The size threshold, or None when the document is set in a single
        font size and size-based detection cannot work.
    """
    largest = body_size
    for index in range(0, doc.page_count, step):
        for block in doc[index].get_text("dict").get("blocks", ()):
            for line in block.get("lines", ()):
                for span in line.get("spans", ()):
                    if span.get("text", "").strip():
                        largest = max(largest, float(span["size"]))
    if largest < body_size * MIN_SIZE_SPREAD:
        return None
    return body_size * HEADING_SIZE_RATIO


def _split_caps_heading(line: str) -> tuple[str | None, str]:
    """Split a leading all-caps chapter head off a line of prose.

    Single-font books run the chapter head straight into the first
    sentence once the PDF line breaks are reflowed, so the head has to be
    recovered from casing rather than layout.

    Args:
        line: A cleaned text line.

    Returns:
        A ``(heading, remainder)`` pair; heading is None when the line
        does not open with a capitalised head.
    """
    match = _CAPS_HEADING_RE.match(line)
    if match is None:
        return None, line
    heading = match.group(1).strip()
    if len(heading) < 5 or not any(c.isalpha() for c in heading):
        return None, line
    return heading, line[match.end() :].strip()


def _page_headings(page: pymupdf.Page, threshold: float | None) -> set[str]:
    """Collect heading lines on a page by font size.

    Args:
        page: The page to inspect.
        threshold: Size at or above which a line is a heading, or None for
            single-font documents where size carries no signal.

    Returns:
        Normalized texts of lines typeset noticeably larger than body text.
    """
    headings: set[str] = set()
    if threshold is None:
        return headings
    for block in page.get_text("dict").get("blocks", ()):
        for line in block.get("lines", ()):
            spans = [s for s in line.get("spans", ()) if s.get("text", "").strip()]
            if not spans:
                continue
            text = _fix_letterspacing(
                " ".join(" ".join(s["text"] for s in spans).split())
            )
            size = max(float(s["size"]) for s in spans)
            if (
                size >= threshold
                and 4 <= len(text) <= MAX_HEADING_CHARS
                and any(c.isalpha() for c in text)
            ):
                headings.add(_normalize_unicode(text))
    return headings


def _reflow(lines: list[str], headings: set[str]) -> str:
    """Rejoin PDF line breaks into paragraphs.

    The text layer breaks at every typeset line, which would leave chunks
    full of sentence fragments. Consecutive lines are merged unless the
    previous line ends a sentence and the next starts a new one.

    Lines identified as headings by font size are kept as standalone
    paragraphs, marked with ``HEADING_MARK`` so Phase 3 can split
    chapters on them.

    Args:
        lines: Cleaned body lines of a page.
        headings: Normalized heading texts found on this page.

    Returns:
        Paragraph-reflowed text.
    """
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        heading, remainder = (
            (line, "") if line in headings else _split_caps_heading(line)
        )
        if heading is not None:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(HEADING_MARK + heading)
            if not remainder:
                continue
            line = remainder
        starts_new = bool(current) and (
            _SENTENCE_END_RE.search(current[-1]) is not None
            and (line[:1].isupper() or line[:1].isdigit())
        )
        if starts_new:
            paragraphs.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def _clean_document(raw_text: str) -> str:
    """Apply document-wide fixes before per-page cleaning.

    Args:
        raw_text: Concatenated raw text of the whole document.

    Returns:
        Text with Gutenberg boilerplate removed and hyphenation repaired.
    """
    if (start := _GUTENBERG_START_RE.search(raw_text)) is not None:
        raw_text = raw_text[start.end():]
    if (end := _GUTENBERG_END_RE.search(raw_text)) is not None:
        raw_text = raw_text[: end.start()]
    return raw_text


def extract_book(book: Book) -> dict[str, object]:
    """Extract and clean one book's typed text.

    Args:
        book: The corpus entry to process.

    Returns:
        A JSON-serialisable record with the book's metadata, cleaned pages,
        and counts of pages skipped for having no usable text layer.
    """
    raw_pages: list[str] = []
    page_headings: list[set[str]] = []
    with pymupdf.open(book.path) as doc:
        step = max(1, doc.page_count // 40)
        body_size = _body_font_size(doc, step)
        threshold = _heading_threshold(doc, body_size, step)
        for page in doc:
            raw_pages.append(_normalize_unicode(page.get_text("text")))
            page_headings.append(_page_headings(page, threshold))

    joined = _clean_document("\n".join(raw_pages))
    raw_pages = joined.split("")

    raw_pages = [_HYPHEN_BREAK_RE.sub(r"\1\2", p) for p in raw_pages]
    line_pages: list[list[str]] = [
        [_fix_letterspacing(" ".join(l.split())) for l in p.splitlines() if l.strip()]
        for p in raw_pages
    ]
    running = _find_running_lines([p for p in line_pages if p])

    pages: list[Page] = []
    skipped: list[int] = []
    for index, lines in enumerate(line_pages, start=1):
        headings = page_headings[index - 1] if index <= len(page_headings) else set()
        body = _reflow(_strip_edges(lines, running), headings).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        if len(body) < MIN_PAGE_CHARS:
            skipped.append(index)
            continue
        pages.append(Page(number=index, text=body))

    return {
        **{k: v for k, v in asdict(book).items()},
        "page_count": len(line_pages),
        "pages_extracted": len(pages),
        "pages_skipped_no_text": len(skipped),
        "skipped_pages_sample": skipped[:30],
        "running_headers_stripped": sorted(running)[:20],
        "total_chars": sum(len(p.text) for p in pages),
        "pages": [asdict(p) for p in pages],
    }


def main() -> None:
    """Extract every corpus book and write per-book JSON."""
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[tuple[str, int, int, int]] = []

    for book in CORPUS:
        print(f"extracting {book.book_id} ...", flush=True)
        record = extract_book(book)
        out = EXTRACT_DIR / f"{book.book_id}.json"
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        summary.append(
            (
                book.book_id,
                int(record["pages_extracted"]),
                int(record["pages_skipped_no_text"]),
                int(record["total_chars"]),
            )
        )

    header = f"{'book_id':<34}{'pages':>7}{'skipped':>9}{'chars':>10}"
    print("\n" + header)
    print("-" * len(header))
    for book_id, kept, skipped, chars in summary:
        print(f"{book_id:<34}{kept:>7}{skipped:>9}{chars:>10}")
    print(f"\nextracted -> {EXTRACT_DIR}")


if __name__ == "__main__":
    main()
