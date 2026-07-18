from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import ETLConfig
from image_utils import calculate_sha256
from sampling import ReservoirItem, SamplingResult


_INVALID_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(slots=True)
class ManifestWriteResult:
    """Result of writing processed images and the JSONL manifest.

    Attributes:
        images_written: Number of images successfully written.
        images_skipped: Number of images skipped because of write errors.
        manifest_path: Path to the generated manifest.
    """

    images_written: int
    images_skipped: int
    manifest_path: Path


def sanitize_filename_component(value: Any) -> str:
    """Convert a value into a safe filename component.

    Args:
        value: Value to sanitize.

    Returns:
        Filesystem-safe string component.
    """
    text = str(value).strip()
    sanitized = _INVALID_FILENAME_CHARACTERS.sub("_", text)
    sanitized = sanitized.strip("._")

    return sanitized or "unknown"


def _get_quality_score(record: Mapping[str, Any]) -> float | int | None:
    """Read an optional source-provided quality score.

    The source dataset may not contain a quality score. In that case, None is
    returned because the ETL specification does not define an image-quality
    scoring model.

    Args:
        record: Dataset record without its image field.

    Returns:
        Numeric quality score when available, otherwise None.
    """
    value = record.get("quality_score")

    if value is None:
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return value

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _create_manifest_entry(
    item: ReservoirItem,
    image_path: Path,
    output_dir: Path,
    image_width: int,
    image_height: int,
    jpeg_quality: int,
    image_hash: str,
    item_index: int,
) -> dict[str, Any]:
    """Create one manifest record for a processed image."""
    record = item.example
    caption = item.caption
    effective_style = record.get("effective_style", "unknown")
    style_component = sanitize_filename_component(effective_style)

    manifest_id = f"{style_component}_{item_index:05d}"

    return {
        "id": manifest_id,
        "image_path": image_path.relative_to(output_dir).as_posix(),
        "artist": record.get("artist"),
        "genre": record.get("genre"),
        "raw_style": record.get("raw_style"),
        "effective_style": record.get("effective_style"),
        "tags": record.get("tags"),
        "caption_original": caption.caption_original,
        "caption_clean": caption.caption_clean,
        "caption_words": caption.caption_words,
        "caption_characters": caption.caption_characters,
        "width": image_width,
        "height": image_height,
        "jpeg_quality": jpeg_quality,
        "sha256": image_hash,
        "quality_score": _get_quality_score(record),
    }


def _write_image(image_path: Path, image_bytes: bytes) -> None:
    """Write JPEG bytes to disk using a temporary file replacement."""
    temporary_path = image_path.with_suffix(".tmp")

    try:
        with temporary_path.open("wb") as image_file:
            image_file.write(image_bytes)

        temporary_path.replace(image_path)

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise


def write_images_and_manifest(
    sampling_result: SamplingResult,
    config: ETLConfig,
    logger: logging.Logger | None = None,
) -> ManifestWriteResult:
    """Write reservoir images and generate the JSONL manifest.

    Images are grouped into directories by effective style. The image bytes
    are already processed JPEG data produced during reservoir sampling.

    Args:
        sampling_result: Reservoir sampling output.
        config: ETL runtime configuration.
        logger: Optional logger for write and serialization errors.

    Returns:
        Summary of successfully written and skipped images.
    """
    active_logger = logger or logging.getLogger(__name__)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.images_dir.mkdir(parents=True, exist_ok=True)

    images_written = 0
    images_skipped = 0

    with config.manifest_path.open("w", encoding="utf-8") as manifest_file:
        for style in sorted(sampling_result.reservoirs):
            items = sampling_result.reservoirs[style]
            style_component = sanitize_filename_component(style)
            style_directory = config.images_dir / style_component
            style_directory.mkdir(parents=True, exist_ok=True)

            for item_index, item in enumerate(items):
                filename = f"{style_component}_{item_index:05d}.jpg"
                image_path = style_directory / filename

                try:
                    _write_image(image_path, item.jpeg_bytes)

                    image_hash = calculate_sha256(item.jpeg_bytes)

                    manifest_entry = _create_manifest_entry(
                        item=item,
                        image_path=image_path,
                        output_dir=config.output_dir,
                        image_width=config.target_size[0],
                        image_height=config.target_size[1],
                        jpeg_quality=config.jpeg_quality,
                        image_hash=image_hash,
                        item_index=item_index,
                    )

                    manifest_file.write(
                        json.dumps(
                            manifest_entry,
                            ensure_ascii=False,
                            default=str,
                        )
                        + "\n"
                    )

                    images_written += 1

                except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    images_skipped += 1
                    active_logger.warning(
                        "Skipping output item '%s': %s",
                        image_path,
                        exc,
                    )

                except Exception as exc:
                    images_skipped += 1
                    active_logger.exception(
                        "Unexpected error while writing '%s': %s",
                        image_path,
                        exc,
                    )

    active_logger.info(
        "Manifest generation completed: %d images written, %d skipped.",
        images_written,
        images_skipped,
    )

    return ManifestWriteResult(
        images_written=images_written,
        images_skipped=images_skipped,
        manifest_path=config.manifest_path,
    )