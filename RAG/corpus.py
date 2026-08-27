"""Corpus definition for the Art-Atelier RAG.

Single source of truth for which PDFs are in scope and how each is
attributed. Titles and authors here were verified against each document's
own front matter during the Phase 0 audit, not inferred from filenames.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

BOOKS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "Art_Books"
EXTRACT_DIR: Final[Path] = Path(__file__).resolve().parent / "extracted"


@dataclass(frozen=True, slots=True)
class Book:
    """One source document in the retrieval corpus.

    Attributes:
        book_id: Stable identifier used as ChromaDB metadata.
        filename: PDF filename under ``Art_Books``.
        title: Title as printed in the document's front matter.
        author: Author as printed in the document's front matter.
        chronological: True when the book is organised by art-historical
            period, making ``periodo_arte`` tagging meaningful.
        subtopic: Optional thematic tag for query-time filtering.
    """

    book_id: str
    filename: str
    title: str
    author: str
    chronological: bool
    subtopic: str | None = None

    @property
    def path(self) -> Path:
        """Absolute path to the source PDF."""
        return BOOKS_DIR / self.filename


#: The six in-scope documents. Two files present in the original
#: RAG_Instructions table (a 7-page encyclopedia entry on color and light,
#: and a 5-page web article on art collecting) were dropped from the corpus
#: by Beau as out of scope for the Melkov agent.
CORPUS: Final[tuple[Book, ...]] = (
    Book(
        book_id="itten_art_of_color",
        filename="THE-ART-OF-COLOR.pdf",
        title="The Art of Color",
        author="Johannes Itten",
        chronological=False,
        subtopic="color_theory",
    ),
    Book(
        book_id="kandinsky_spiritual_in_art",
        filename="Wassily_Kandinsky_Concerning_the_Spiritu.pdf",
        title="Concerning the Spiritual in Art",
        author="Wassily Kandinsky",
        chronological=False,
    ),
    Book(
        book_id="faure_history_of_art",
        filename="History_of_Art.pdf",
        title="History of Art: Ancient Art",
        author="Elie Faure",
        chronological=True,
    ),
    Book(
        book_id="arnheim_art_visual_perception",
        filename="Art-And-Visual-Perception_text.pdf",
        title="Art and Visual Perception: A Psychology of the Creative Eye",
        author="Rudolf Arnheim",
        chronological=False,
        subtopic="perception",
    ),
    Book(
        # Third-party lecture notes ON Arnheim, not written by Arnheim.
        book_id="leymarie_arnheim_notes",
        filename="Art_and_Visual_Perception_by_Rudolph_Arn.pdf",
        title="Art and Visual Perception (summary notes)",
        author="Frederic F. Leymarie",
        chronological=False,
        subtopic="perception",
    ),
    Book(
        book_id="gombrich_story_of_art",
        filename="dokumen.pub_the-story-of-art-4thnbsped.pdf",
        title="The Story of Art (4th ed.)",
        author="E. H. Gombrich",
        chronological=True,
    ),
)
