"""Phase 0 audit of the Art_Books PDF corpus.

Reports, per document: page count, character volume, per-page character
density (to flag pages lacking a text layer), a column-layout heuristic
derived from text-block x0 clustering, embedded-image density, and the
title/author as they appear on the document's own front matter.

Writes ``audit_report.json`` and prints a human-readable summary table.
No extraction or chunking decisions are made here — this output is the
input to those decisions.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import pymupdf

BOOKS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "Art_Books"
REPORT_PATH: Final[Path] = Path(__file__).resolve().parent / "audit_report.json"

#: Pages below this fraction of the document's median chars/page are treated
#: as candidates for having no usable text layer (i.e. scanned images).
LOW_TEXT_RATIO: Final[float] = 0.20
#: A page needs at least this many text blocks before its x0 distribution is
#: considered meaningful for column detection.
MIN_BLOCKS_FOR_COLUMNS: Final[int] = 6
#: Fraction of sampled pages that must look bimodal to call a book 2-column.
BIMODAL_PAGE_THRESHOLD: Final[float] = 0.40
#: Pages sampled (evenly spaced) for the layout heuristic on large books.
LAYOUT_SAMPLE_SIZE: Final[int] = 40
#: Characters pulled from the first pages when guessing title/author.
FRONT_MATTER_CHARS: Final[int] = 700


@dataclass(slots=True)
class PageStats:
    """Per-page measurements collected in a single pass."""

    index: int
    chars: int
    blocks: int
    images: int
    x0_values: list[float] = field(default_factory=list)


def _is_bimodal(x0_values: list[float], page_width: float) -> bool:
    """Return True if block x0 positions suggest a two-column page.

    Splits the x0 values at the page midpoint and requires both sides to
    hold a substantial share of blocks, with a clear gap between the two
    groups' centres. A single-column page puts nearly every block on the
    left of the midpoint.

    Args:
        x0_values: Left edges of the page's text blocks.
        page_width: Width of the page in points.

    Returns:
        True when the distribution looks like two distinct columns.
    """
    if len(x0_values) < MIN_BLOCKS_FOR_COLUMNS:
        return False
    midpoint = page_width / 2
    left = [x for x in x0_values if x < midpoint]
    right = [x for x in x0_values if x >= midpoint]
    if not left or not right:
        return False
    minority = min(len(left), len(right)) / len(x0_values)
    if minority < 0.25:
        return False
    gap = statistics.median(right) - statistics.median(left)
    return gap > page_width * 0.25


def _guess_front_matter(doc: pymupdf.Document) -> dict[str, Any]:
    """Collect title/author candidates from metadata and the first pages.

    Args:
        doc: An open PyMuPDF document.

    Returns:
        Mapping with embedded PDF metadata plus the raw opening text, so a
        human can confirm the real title rather than trusting the filename.
    """
    meta = doc.metadata or {}
    opening: list[str] = []
    for page_index in range(min(3, doc.page_count)):
        text = doc[page_index].get_text().strip()
        if text:
            opening.append(text[:FRONT_MATTER_CHARS])
    return {
        "metadata_title": (meta.get("title") or "").strip() or None,
        "metadata_author": (meta.get("author") or "").strip() or None,
        "front_matter_text": "\n---\n".join(opening),
    }


def audit_pdf(path: Path) -> dict[str, Any]:
    """Audit a single PDF and return its report entry.

    Args:
        path: Path to the PDF file.

    Returns:
        A JSON-serialisable dict describing the document's text density,
        layout, image content, and front matter.
    """
    with pymupdf.open(path) as doc:
        page_count = doc.page_count
        sample_step = max(1, page_count // LAYOUT_SAMPLE_SIZE)
        pages: list[PageStats] = []
        widths: list[float] = []

        for index, page in enumerate(doc):
            text = page.get_text()
            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if len(b) > 6 and b[6] == 0]
            stats = PageStats(
                index=index,
                chars=len(text),
                blocks=len(text_blocks),
                images=len(page.get_images(full=True)),
            )
            if index % sample_step == 0:
                stats.x0_values = [float(b[0]) for b in text_blocks]
                widths.append(float(page.rect.width))
            pages.append(stats)

        front_matter = _guess_front_matter(doc)

    char_counts = [p.chars for p in pages]
    total_chars = sum(char_counts)
    median_chars = statistics.median(char_counts) if char_counts else 0.0
    threshold = median_chars * LOW_TEXT_RATIO

    low_text_pages = [
        p.index for p in pages if p.chars < threshold or p.chars < 50
    ]
    sampled = [p for p in pages if p.x0_values]
    page_width = statistics.median(widths) if widths else 612.0
    bimodal_pages = [
        p.index for p in sampled if _is_bimodal(p.x0_values, page_width)
    ]
    bimodal_fraction = len(bimodal_pages) / len(sampled) if sampled else 0.0
    pages_with_images = [p.index for p in pages if p.images > 0]

    return {
        "filename": path.name,
        "size_mb": round(path.stat().st_size / 1_048_576, 2),
        "page_count": page_count,
        "total_chars": total_chars,
        "chars_per_page_mean": round(total_chars / page_count, 1) if page_count else 0,
        "chars_per_page_median": round(median_chars, 1),
        "low_text_page_count": len(low_text_pages),
        "low_text_page_fraction": round(len(low_text_pages) / page_count, 3)
        if page_count
        else 0.0,
        "low_text_pages_sample": low_text_pages[:40],
        "layout_pages_sampled": len(sampled),
        "bimodal_page_fraction": round(bimodal_fraction, 3),
        "likely_two_column": bimodal_fraction >= BIMODAL_PAGE_THRESHOLD,
        "total_images": sum(p.images for p in pages),
        "pages_with_images_fraction": round(len(pages_with_images) / page_count, 3)
        if page_count
        else 0.0,
        **front_matter,
    }


def main() -> None:
    """Audit every PDF in ``Art_Books`` and write the Phase 0 report."""
    pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {BOOKS_DIR}")

    report: list[dict[str, Any]] = []
    for path in pdfs:
        print(f"auditing {path.name} ...", flush=True)
        report.append(audit_pdf(path))

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    header = (
        f"{'file':<46}{'pages':>7}{'ch/pg':>8}{'lowtxt':>8}"
        f"{'2col':>7}{'imgpg':>7}"
    )
    print("\n" + header)
    print("-" * len(header))
    for entry in report:
        print(
            f"{entry['filename'][:45]:<46}"
            f"{entry['page_count']:>7}"
            f"{entry['chars_per_page_median']:>8.0f}"
            f"{entry['low_text_page_count']:>8}"
            f"{'yes' if entry['likely_two_column'] else 'no':>7}"
            f"{entry['pages_with_images_fraction']:>7.2f}"
        )
    print(f"\nreport -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
