import re
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from config import (
    CAPTION_FIELD_CANDIDATES,
    MIN_CAPTION_CHARACTERS,
    MIN_CAPTION_WORDS,
)


_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CaptionResult:
    """Result of caption construction and validation.

    Attributes:
        caption_original: Caption assembled from source fields before
            whitespace normalization.
        caption_clean: Caption after whitespace normalization only.
        caption_words: Number of whitespace-separated words.
        caption_characters: Number of characters in the cleaned caption.
        is_valid: Whether the caption satisfies the configured thresholds.
    """

    caption_original: str
    caption_clean: str
    caption_words: int
    caption_characters: int
    is_valid: bool


def _stringify_value(value: Any) -> str:
    """Convert a source field value into usable caption text.

    Lists and tuples are joined using commas. Other values are converted
    using their string representation. Missing values return an empty string.

    Args:
        value: Source field value.

    Returns:
        A string representation suitable for caption construction.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (list, tuple)):
        parts = [
            str(item).strip()
            for item in value
            if item is not None and str(item).strip()
        ]
        return ", ".join(parts)

    if isinstance(value, Mapping):
        parts = [
            f"{key}: {item}"
            for key, item in value.items()
            if item is not None and str(item).strip()
        ]
        return ", ".join(parts).strip()

    return str(value).strip()


def normalize_caption(text: str) -> str:
    """Normalize caption whitespace without changing its meaning.

    This function does not perform semantic cleaning, rewriting, translation,
    grammar correction, or LLM-based recaptioning.

    Args:
        text: Caption text to normalize.

    Returns:
        Caption with repeated whitespace and line breaks replaced by single
        spaces.
    """
    if not isinstance(text, str):
        raise TypeError("Caption text must be a string.")

    return _WHITESPACE_PATTERN.sub(" ", text).strip()


def count_caption_words(text: str) -> int:
    """Count whitespace-separated words in a caption.

    Args:
        text: Caption text.

    Returns:
        Number of words in the caption.
    """
    normalized_text = normalize_caption(text)
    if not normalized_text:
        return 0

    return len(normalized_text.split())


def count_caption_characters(text: str) -> int:
    """Count characters in a normalized caption.

    Args:
        text: Caption text.

    Returns:
        Number of characters after whitespace normalization.
    """
    return len(normalize_caption(text))


def is_caption_valid(
    text: str,
    min_words: int = MIN_CAPTION_WORDS,
    min_characters: int = MIN_CAPTION_CHARACTERS,
) -> bool:
    """Determine whether a caption meets the minimum quality thresholds.

    A caption is rejected if it has fewer than ``min_words`` words or fewer
    than ``min_characters`` characters.

    Args:
        text: Caption text to validate.
        min_words: Minimum required word count.
        min_characters: Minimum required character count.

    Returns:
        True if the caption satisfies both thresholds; otherwise, False.

    Raises:
        ValueError: If either threshold is negative.
    """
    if min_words < 0:
        raise ValueError("min_words cannot be negative.")

    if min_characters < 0:
        raise ValueError("min_characters cannot be negative.")

    normalized_text = normalize_caption(text)

    return (
        count_caption_words(normalized_text) >= min_words
        and len(normalized_text) >= min_characters
    )


def _build_caption_parts(example: Mapping[str, Any]) -> list[str]:
    """Extract caption parts from the configured source fields.

    Args:
        example: Dataset example containing potential caption fields.

    Returns:
        Non-empty caption components in configured field order.
    """
    parts: list[str] = []

    for field_name in CAPTION_FIELD_CANDIDATES:
        try:
            value = example.get(field_name)
            text = _stringify_value(value)
        except Exception:
            # A malformed field should not invalidate the complete record.
            continue

        if text:
            parts.append(text)

    return parts


def _build_tag_fallback(example: Mapping[str, Any]) -> str:
    """Build fallback caption text from the source tags field.

    Args:
        example: Dataset example containing an optional ``tags`` field.

    Returns:
        Comma-separated tag text, or an empty string when unavailable.
    """
    try:
        tags = example.get("tags")
    except Exception:
        return ""

    if tags is None:
        return ""

    if isinstance(tags, str):
        return tags.strip()

    if isinstance(tags, Sequence) and not isinstance(tags, (bytes, bytearray)):
        tag_values = [
            str(tag).strip()
            for tag in tags[:20]
            if tag is not None and str(tag).strip()
        ]
        return ", ".join(tag_values)

    return _stringify_value(tags)


def build_caption_text(example: Mapping[str, Any]) -> str:
    """Build caption text from the available dataset fields.

    Configured descriptive fields are concatenated in their defined order.
    The ``tags`` field is used only when no descriptive fields are available.

    Args:
        example: Dataset example from the streamed dataset.

    Returns:
        Assembled caption text before whitespace normalization.
    """
    parts = _build_caption_parts(example)

    if not parts:
        tag_fallback = _build_tag_fallback(example)
        if tag_fallback:
            parts.append(tag_fallback)

    return " ".join(parts).strip()


def build_caption_result(
    example: Mapping[str, Any],
    min_words: int = MIN_CAPTION_WORDS,
    min_characters: int = MIN_CAPTION_CHARACTERS,
) -> CaptionResult:
    """Build and validate a caption for a dataset example.

    Only whitespace normalization is applied. The source content is not
    rewritten, enriched, translated, or recaptioned.

    Args:
        example: Dataset example from the streamed dataset.
        min_words: Minimum required word count.
        min_characters: Minimum required character count.

    Returns:
        A ``CaptionResult`` containing caption text, counts, and validity.
    """
    caption_original = build_caption_text(example)
    caption_clean = normalize_caption(caption_original)
    caption_words = count_caption_words(caption_clean)
    caption_characters = len(caption_clean)

    valid = (
        caption_words >= min_words
        and caption_characters >= min_characters
    )

    return CaptionResult(
        caption_original=caption_original,
        caption_clean=caption_clean,
        caption_words=caption_words,
        caption_characters=caption_characters,
        is_valid=valid,
    )