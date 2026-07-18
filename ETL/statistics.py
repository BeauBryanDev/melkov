from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ETLConfig
from manifest import ManifestWriteResult
from sampling import ReservoirItem, SamplingResult


def _count_values(
    values: Iterable[Any],
    unknown_label: str = "Unknown",
) -> dict[str, int]:
    """Count normalized values while handling missing fields."""
    counter: Counter[str] = Counter()

    for value in values:
        if value is None:
            normalized_value = unknown_label
        else:
            normalized_value = str(value).strip() or unknown_label

        counter[normalized_value] += 1

    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _iter_reservoir_items(
    sampling_result: SamplingResult,
) -> Iterable[ReservoirItem]:
    """Yield all successfully processed reservoir items."""
    for items in sampling_result.reservoirs.values():
        yield from items


def _calculate_directory_size(directory: Path) -> int:
    """Calculate the total size of regular files in a directory."""
    if not directory.exists():
        return 0

    total_size = 0

    for path in directory.rglob("*"):
        if path.is_file():
            try:
                total_size += path.stat().st_size
            except OSError:
                continue

    return total_size


def _caption_statistics(
    items: list[ReservoirItem],
) -> dict[str, Any]:
    """Calculate caption count and length statistics."""
    word_counts = [item.caption.caption_words for item in items]
    character_counts = [item.caption.caption_characters for item in items]

    if not word_counts:
        return {
            "valid_captions": 0,
            "average_words": 0.0,
            "average_characters": 0.0,
            "minimum_words": 0,
            "maximum_words": 0,
            "minimum_characters": 0,
            "maximum_characters": 0,
        }

    return {
        "valid_captions": len(word_counts),
        "average_words": round(sum(word_counts) / len(word_counts), 2),
        "average_characters": round(
            sum(character_counts) / len(character_counts),
            2,
        ),
        "minimum_words": min(word_counts),
        "maximum_words": max(word_counts),
        "minimum_characters": min(character_counts),
        "maximum_characters": max(character_counts),
    }


def _style_distribution(
    sampling_result: SamplingResult,
) -> dict[str, int]:
    """Calculate the number of retained images per effective style."""
    distribution = {
        style: len(items)
        for style, items in sampling_result.reservoirs.items()
    }

    return dict(
        sorted(
            distribution.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _artist_distribution(
    items: list[ReservoirItem],
) -> dict[str, int]:
    """Calculate artist frequency among retained images."""
    return _count_values(
        item.example.get("artist")
        for item in items
    )


def _genre_distribution(
    items: list[ReservoirItem],
) -> dict[str, int]:
    """Calculate genre frequency among retained images."""
    return _count_values(
        item.example.get("genre")
        for item in items
    )


def build_statistics(
    sampling_result: SamplingResult,
    manifest_result: ManifestWriteResult,
    config: ETLConfig,
    start_time: float,
    end_time: float | None = None,
) -> dict[str, Any]:
    """Build the complete dataset statistics structure.

    Args:
        sampling_result: Result of streaming and reservoir sampling.
        manifest_result: Result of image and manifest writing.
        config: ETL runtime configuration.
        start_time: Monotonic timestamp captured at ETL start.
        end_time: Optional monotonic completion timestamp. The current time is
            used when omitted.

    Returns:
        JSON-serializable statistics dictionary.
    """
    completion_time = end_time if end_time is not None else time.monotonic()
    execution_seconds = max(0.0, completion_time - start_time)

    items = list(_iter_reservoir_items(sampling_result))
    counters = sampling_result.counters

    style_distribution = _style_distribution(sampling_result)

    records_skipped = {
        "excluded_styles": counters.excluded_seen,
        "unknown_styles": counters.unknown_style_seen,
        "invalid_captions": counters.invalid_caption_seen,
        "corrupted_images": counters.corrupted_image_seen,
        "missing_fields": counters.missing_field_seen,
        "processing_errors": counters.processing_error_seen,
        "manifest_write_errors": manifest_result.images_skipped,
    }

    total_records_skipped = sum(records_skipped.values())

    return {
        "dataset_name": "Aegis-Art-Atelier-22K",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "images_written": manifest_result.images_written,
        "images_skipped": manifest_result.images_skipped,
        "records_seen": counters.total_seen,
        "records_eligible": counters.eligible_seen,
        "records_skipped": total_records_skipped,
        "skip_breakdown": records_skipped,
        "caption_statistics": {
            **_caption_statistics(items),
            "invalid_captions": counters.invalid_caption_seen,
            "minimum_required_words": config.min_caption_words,
            "minimum_required_characters": (
                config.min_caption_characters
            ),
        },
        "style_distribution": style_distribution,
        "artist_distribution": _artist_distribution(items),
        "genre_distribution": _genre_distribution(items),
        "eligible_records_by_style": dict(
            sorted(sampling_result.eligible_by_style.items())
        ),
        "unknown_styles": sorted(counters.unknown_styles),
        "excluded_styles": dict(
            sorted(counters.excluded_styles.items())
        ),
        "execution": {
            "seconds": round(execution_seconds, 3),
            "minutes": round(execution_seconds / 60, 3),
            "records_per_second": round(
                counters.total_seen / execution_seconds,
                3,
            )
            if execution_seconds > 0
            else 0.0,
            "images_per_second": round(
                manifest_result.images_written / execution_seconds,
                3,
            )
            if execution_seconds > 0
            else 0.0,
        },
        "dataset_size": {
            "bytes": _calculate_directory_size(config.output_dir),
            "megabytes": round(
                _calculate_directory_size(config.output_dir) / (1024**2),
                3,
            ),
            "gigabytes": round(
                _calculate_directory_size(config.output_dir) / (1024**3),
                6,
            ),
        },
    }


def write_statistics(
    statistics: Mapping[str, Any],
    output_path: Path,
    logger: logging.Logger | None = None,
) -> Path:
    """Write statistics to a UTF-8 JSON file.

    Args:
        statistics: JSON-serializable statistics mapping.
        output_path: Destination path.
        logger: Optional logger for completion reporting.

    Returns:
        The written statistics path.
    """
    active_logger = logger or logging.getLogger(__name__)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as statistics_file:
        json.dump(
            statistics,
            statistics_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
        statistics_file.write("\n")

    active_logger.info("Statistics written to %s", output_path)

    return output_path