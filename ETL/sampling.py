import logging
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from tqdm.auto import tqdm

from ETL.caption_utils import CaptionResult, build_caption_result
from ETL.config import ETLConfig, STYLE_CAPS, STYLE_EXCLUDE, STYLE_MERGE
from ETL.image_utils import ImageProcessingError, encode_image_field


@dataclass(slots=True)
class ReservoirItem:
    """A processed item stored in a style reservoir.

    Attributes:
        example: Original example fields excluding the image field.
        jpeg_bytes: Processed JPEG image bytes.
        caption: Validated caption information.
    """

    example: dict[str, Any]
    jpeg_bytes: bytes
    caption: CaptionResult


@dataclass(slots=True)
class SamplingCounters:
    """Counters collected during streaming and reservoir sampling."""

    total_seen: int = 0
    eligible_seen: int = 0
    excluded_seen: int = 0
    unknown_style_seen: int = 0
    invalid_caption_seen: int = 0
    corrupted_image_seen: int = 0
    missing_field_seen: int = 0
    processing_error_seen: int = 0

    unknown_styles: set[str] = field(default_factory=set)
    excluded_styles: dict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    skipped_image_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SamplingResult:
    """Result of streaming reservoir sampling.

    Attributes:
        reservoirs: Processed records grouped by effective style.
        counters: Processing counters and skip information.
        eligible_by_style: Number of caption-valid records seen per style.
    """

    reservoirs: dict[str, list[ReservoirItem]]
    counters: SamplingCounters
    eligible_by_style: dict[str, int]


def resolve_style(raw_style: Any) -> str | None:
    """Resolve a raw style into its effective style bucket.

    Styles in ``STYLE_EXCLUDE`` are discarded. Styles in ``STYLE_MERGE`` are
    mapped to their destination bucket. Unknown or missing styles return
    ``None`` and are handled by the caller.

    Args:
        raw_style: Raw style value from the dataset record.

    Returns:
        Effective style name, or None when the style is excluded or missing.
    """
    if raw_style is None:
        return None

    if not isinstance(raw_style, str):
        raw_style = str(raw_style).strip()

    if not raw_style:
        return None

    if raw_style in STYLE_EXCLUDE:
        return None

    return STYLE_MERGE.get(raw_style, raw_style)


def _style_is_excluded(raw_style: Any) -> bool:
    """Return whether a raw style is explicitly excluded."""
    if raw_style is None:
        return False

    style_name = str(raw_style).strip()
    return style_name in STYLE_EXCLUDE


def _copy_example_without_image(
    example: Mapping[str, Any],
    raw_style: Any,
    effective_style: str,
) -> dict[str, Any]:
    """Copy a source example while removing its image field."""
    record = dict(example)
    record.pop("image", None)
    record["raw_style"] = raw_style
    record["effective_style"] = effective_style
    return record


def _reservoir_size(
    reservoirs: Mapping[str, list[ReservoirItem]],
) -> int:
    """Return the total number of successfully stored images."""
    return sum(len(items) for items in reservoirs.values())


def _update_progress(
    progress: tqdm,
    current_style: str | None,
    reservoirs: Mapping[str, list[ReservoirItem]],
) -> None:
    """Update the streaming progress display."""
    progress.set_postfix(
        style=current_style or "unknown",
        reservoir=_reservoir_size(reservoirs),
    )


def _store_candidate(
    reservoir: list[ReservoirItem],
    candidate: ReservoirItem,
    seen_count: int,
    cap: int,
    rng: random.Random,
) -> None:
    """Apply reservoir sampling to one processed candidate.

    Args:
        reservoir: Reservoir for one effective style.
        candidate: Successfully processed candidate.
        seen_count: Number of eligible candidates seen for this style.
        cap: Maximum reservoir size for the style.
        rng: Dedicated random number generator.
    """
    if len(reservoir) < cap:
        reservoir.append(candidate)
        return

    replacement_index = rng.randint(1, seen_count)

    if replacement_index <= cap:
        reservoir[replacement_index - 1] = candidate


def _process_selected_candidate(
    example: Mapping[str, Any],
    raw_style: Any,
    effective_style: str,
    caption: CaptionResult,
    config: ETLConfig,
) -> ReservoirItem:
    """Decode and process an image selected for reservoir storage.

    Image decoding intentionally occurs only after the candidate has passed
    style and caption filtering and has been selected for reservoir storage.

    Args:
        example: Original streamed dataset example.
        raw_style: Original raw style.
        effective_style: Resolved style bucket.
        caption: Validated caption information.
        config: ETL runtime configuration.

    Returns:
        A processed reservoir item.

    Raises:
        ImageProcessingError: If the image cannot be decoded or encoded.
        KeyError: If the image field is missing.
    """
    image_field = example["image"]

    jpeg_bytes = encode_image_field(
        image_field=image_field,
        target_size=config.target_size,
        jpeg_quality=config.jpeg_quality,
    )

    record = _copy_example_without_image(
        example=example,
        raw_style=raw_style,
        effective_style=effective_style,
    )

    return ReservoirItem(
        example=record,
        jpeg_bytes=jpeg_bytes,
        caption=caption,
    )


def sample_stream(
    dataset: Iterable[Mapping[str, Any]],
    config: ETLConfig,
    logger: logging.Logger | None = None,
) -> SamplingResult:
    """Stream a dataset and perform per-style reservoir sampling.

    The supplied dataset must already be configured for streaming. This
    function does not shuffle the dataset and never loads it into memory.

    Caption validation occurs before image decoding. Images are decoded only
    when a record is selected for insertion or replacement in its style
    reservoir.

    Args:
        dataset: Streaming iterable of dataset examples.
        config: ETL runtime configuration.
        logger: Optional logger for warnings and error reporting.

    Returns:
        Sampling results containing reservoirs and processing counters.
    """
    active_logger = logger or logging.getLogger(__name__)
    rng = random.Random(config.seed)

    reservoirs: dict[str, list[ReservoirItem]] = defaultdict(list)
    eligible_by_style: dict[str, int] = defaultdict(int)
    seen_by_style: dict[str, int] = defaultdict(int)
    counters = SamplingCounters()

    progress = tqdm(
        dataset,
        desc="Streaming dataset",
        unit="record",
        dynamic_ncols=True,
    )

    try:
        for example in progress:
            counters.total_seen += 1

            if config.dry_run is not None:
                if counters.total_seen > config.dry_run:
                    break

            if not isinstance(example, Mapping):
                counters.missing_field_seen += 1
                active_logger.warning(
                    "Skipping record %d because it is not a mapping.",
                    counters.total_seen,
                )
                continue

            raw_style = example.get("style")
            effective_style = resolve_style(raw_style)

            if _style_is_excluded(raw_style):
                counters.excluded_seen += 1
                counters.excluded_styles[str(raw_style)] += 1
                _update_progress(progress, str(raw_style), reservoirs)
                continue

            if effective_style is None:
                counters.unknown_style_seen += 1
                counters.unknown_styles.add(str(raw_style))
                _update_progress(progress, None, reservoirs)
                continue

            if effective_style not in STYLE_CAPS:
                counters.unknown_style_seen += 1
                counters.unknown_styles.add(str(raw_style))
                _update_progress(progress, effective_style, reservoirs)
                continue

            if "image" not in example:
                counters.missing_field_seen += 1
                active_logger.warning(
                    "Skipping record %d with style '%s': image field missing.",
                    counters.total_seen,
                    effective_style,
                )
                _update_progress(progress, effective_style, reservoirs)
                continue

            try:
                caption = build_caption_result(
                    example=example,
                    min_words=config.min_caption_words,
                    min_characters=config.min_caption_characters,
                )
            except Exception as exc:
                counters.processing_error_seen += 1
                active_logger.warning(
                    "Caption processing failed for record %d: %s",
                    counters.total_seen,
                    exc,
                )
                _update_progress(progress, effective_style, reservoirs)
                continue

            if not caption.is_valid:
                counters.invalid_caption_seen += 1
                _update_progress(progress, effective_style, reservoirs)
                continue

            counters.eligible_seen += 1
            seen_by_style[effective_style] += 1
            eligible_by_style[effective_style] += 1

            cap = STYLE_CAPS[effective_style]
            current_reservoir = reservoirs[effective_style]
            seen_count = seen_by_style[effective_style]

            should_process = len(current_reservoir) < cap

            if not should_process:
                replacement_index = rng.randint(1, seen_count)
                should_process = replacement_index <= cap
            else:
                replacement_index = None

            if not should_process:
                _update_progress(progress, effective_style, reservoirs)
                continue

            try:
                candidate = _process_selected_candidate(
                    example=example,
                    raw_style=raw_style,
                    effective_style=effective_style,
                    caption=caption,
                    config=config,
                )

                if len(current_reservoir) < cap:
                    _store_candidate(current_reservoir, candidate, seen_count, cap, rng)
                elif replacement_index is not None:
                    current_reservoir[replacement_index - 1] = candidate

            except ImageProcessingError as exc:
                counters.corrupted_image_seen += 1
                if len(counters.skipped_image_errors) < 100:
                    counters.skipped_image_errors.append(str(exc))

                active_logger.warning(
                    "Skipping corrupted image at record %d, style '%s': %s",
                    counters.total_seen,
                    effective_style,
                    exc,
                )

            except KeyError as exc:
                counters.missing_field_seen += 1
                active_logger.warning(
                    "Skipping record %d, style '%s': missing field %s",
                    counters.total_seen,
                    effective_style,
                    exc,
                )

            except Exception as exc:
                counters.processing_error_seen += 1
                active_logger.exception(
                    "Unexpected processing error at record %d: %s",
                    counters.total_seen,
                    exc,
                )

            _update_progress(progress, effective_style, reservoirs)

    finally:
        progress.close()

    return SamplingResult(
        reservoirs=dict(reservoirs),
        counters=counters,
        eligible_by_style=dict(eligible_by_style),
    )