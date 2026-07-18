from __future__ import annotations

import argparse
import ast
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ETL.build_single_file import _is_future_import, _is_internal_import, _is_module_docstring
from datasets import Image as HFImage
from datasets import load_dataset

from compression import (
    CompressionResult,
    compress_dataset,
    copy_archive_to_directory,
)
from config import (
    DATASET_NAME,
    DATASET_OUTPUT_NAME,
    DATASET_SPLIT,
    DATASET_VERSION,
    JPEG_QUALITY,
    STYLE_CAPS,
    STYLE_EXCLUDE,
    STYLE_MERGE,
    TARGET_SIZE,
    ETLConfig,
)
from manifest import ManifestWriteResult, write_images_and_manifest
from sampling import SamplingResult, sample_stream
from statistics import build_statistics, write_statistics


LOGGER_NAME = "aegis_art_atelier"


@dataclass(slots=True)
class ETLRunResult:
    """Result of a complete ETL execution.

    Attributes:
        output_dir: Dataset output directory.
        archive_path: Generated tar.gz archive.
        images_written: Number of successfully written images.
        sampling_result: Streaming and reservoir sampling result.
        manifest_result: Manifest generation result.
        compression_result: Compression result.
        drive_copy_path: Optional Google Drive copy path.
    """

    output_dir: Path
    archive_path: Path
    images_written: int
    sampling_result: SamplingResult
    manifest_result: ManifestWriteResult
    compression_result: CompressionResult
    drive_copy_path: Path | None = None


def configure_logging(log_path: Path) -> logging.Logger:
    """Configure console and file logging for the ETL process.

    Args:
        log_path: Destination path for the ETL log file.

    Returns:
        Configured ETL logger.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def load_streaming_dataset(config: ETLConfig) -> Any:
    """Load the Hugging Face dataset in streaming mode.

    Image decoding is disabled at the dataset level. Images are decoded later
    only when selected for reservoir insertion or replacement.

    Args:
        config: ETL runtime configuration.

    Returns:
        Streaming Hugging Face dataset.

    Raises:
        RuntimeError: If the dataset cannot be loaded or the image column
            cannot be configured for manual decoding.
    """
    try:
        dataset = load_dataset(
            config.dataset_name,
            split=config.dataset_split,
            streaming=True,
        )

        dataset = dataset.cast_column(
            "image",
            HFImage(decode=False),
        )

        return dataset

    except Exception as exc:
        raise RuntimeError(
            "Unable to load the dataset in streaming mode."
        ) from exc


def build_dataset_info(
    config: ETLConfig,
    images_written: int,
    created_at: str,
) -> dict[str, Any]:
    """Build the dataset metadata structure."""
    return {
        "dataset_name": DATASET_OUTPUT_NAME,
        "dataset_version": DATASET_VERSION,
        "creation_date": created_at,
        "dataset_source": config.dataset_name,
        "dataset_split": config.dataset_split,
        "resolution": {
            "width": config.target_size[0],
            "height": config.target_size[1],
        },
        "jpeg_quality": config.jpeg_quality,
        "sampling_algorithm": "Per-style reservoir sampling",
        "streaming": True,
        "shuffle": False,
        "seed": config.seed,
        "style_caps": STYLE_CAPS,
        "merged_styles": STYLE_MERGE,
        "excluded_styles": sorted(STYLE_EXCLUDE),
        "caption_validation": {
            "minimum_words": config.min_caption_words,
            "minimum_characters": config.min_caption_characters,
            "llm_cleaning": False,
            "recaptioning": False,
        },
        "number_of_images": images_written,
    }


def _remove_source_ranges(
    source: str,
    tree: ast.Module,
    is_first_module: bool,
) -> tuple[str, bool]:
    """Remove imports that cannot remain in the merged file.!"""
    source_lines = source.splitlines(keepends=True)
    ranges_to_remove: list[tuple[int, int]] = []
    found_future_import = False

    for node in tree.body:
        should_remove = False

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if _is_internal_import(node):
                should_remove = True
            elif _is_future_import(node):
                found_future_import = True
                should_remove = True

        if _is_module_docstring(node, is_first_module):
            should_remove = True

        if should_remove:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            ranges_to_remove.append((start_line, end_line))

    for start_line, end_line in ranges_to_remove:
        for line_index in range(start_line, end_line):
            source_lines[line_index] = ""

    return "".join(source_lines), found_future_import
    

def write_dataset_info(
    config: ETLConfig,
    images_written: int,
    created_at: str,
    logger: logging.Logger,
) -> Path:
    """Write dataset metadata to dataset_info.json."""
    dataset_info = build_dataset_info(
        config=config,
        images_written=images_written,
        created_at=created_at,
    )

    with config.dataset_info_path.open("w", encoding="utf-8") as info_file:
        json.dump(
            dataset_info,
            info_file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        info_file.write("\n")

    logger.info("Dataset metadata written to %s", config.dataset_info_path)

    return config.dataset_info_path


def run_etl(config: ETLConfig) -> ETLRunResult:
    """Execute the complete Aegis-Art-Atelier ETL pipeline.

    Args:
        config: ETL runtime configuration.

    Returns:
        Complete ETL execution result.
    """
    start_time = time.monotonic()
    created_at = datetime.now(timezone.utc).isoformat()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    logger = configure_logging(config.log_path)

    logger.info("Starting %s ETL pipeline.", DATASET_OUTPUT_NAME)
    logger.info("Dataset source: %s", config.dataset_name)
    logger.info("Streaming mode: enabled")
    logger.info("Dataset shuffle: disabled")
    logger.info("Output directory: %s", config.output_dir)
    logger.info("Random seed: %d", config.seed)
    logger.info(
        "Target image size: %dx%d",
        config.target_size[0],
        config.target_size[1],
    )
    logger.info("JPEG quality: %d", config.jpeg_quality)

    if any(config.output_dir.iterdir()):
        logger.warning(
            "Output directory already contains files. Existing files may be "
            "overwritten or included in the final archive."
        )

    logger.info("Loading Hugging Face dataset in streaming mode.")
    dataset = load_streaming_dataset(config)

    logger.info("Starting style-aware reservoir sampling.")
    sampling_result = sample_stream(
        dataset=dataset,
        config=config,
        logger=logger,
    )

    logger.info(
        "Sampling completed. Records seen: %d; eligible records: %d; "
        "reservoir images: %d",
        sampling_result.counters.total_seen,
        sampling_result.counters.eligible_seen,
        sum(
            len(items)
            for items in sampling_result.reservoirs.values()
        ),
    )

    logger.info("Writing processed images and manifest.")
    manifest_result = write_images_and_manifest(
        sampling_result=sampling_result,
        config=config,
        logger=logger,
    )

    write_dataset_info(
        config=config,
        images_written=manifest_result.images_written,
        created_at=created_at,
        logger=logger,
    )

    end_time = time.monotonic()

    statistics = build_statistics(
        sampling_result=sampling_result,
        manifest_result=manifest_result,
        config=config,
        start_time=start_time,
        end_time=end_time,
    )

    write_statistics(
        statistics=statistics,
        output_path=config.stats_path,
        logger=logger,
    )

    logger.info("Compressing completed dataset.")
    compression_result = compress_dataset(
        output_dir=config.output_dir,
        archive_path=config.archive_path,
        logger=logger,
    )

    drive_copy_path: Path | None = None

    if config.drive_output is not None:
        drive_copy_path = copy_archive_to_directory(
            archive_path=compression_result.archive_path,
            destination_dir=config.drive_output,
            logger=logger,
        )

    total_elapsed = time.monotonic() - start_time

    logger.info(
        "ETL pipeline completed successfully in %.2f minutes.",
        total_elapsed / 60,
    )
    logger.info("Images written: %d", manifest_result.images_written)
    logger.info("Archive: %s", compression_result.archive_path)

    if drive_copy_path is not None:
        logger.info("Google Drive copy: %s", drive_copy_path)

    return ETLRunResult(
        output_dir=config.output_dir,
        archive_path=compression_result.archive_path,
        images_written=manifest_result.images_written,
        sampling_result=sampling_result,
        manifest_result=manifest_result,
        compression_result=compression_result,
        drive_copy_path=drive_copy_path,
    )


def parse_arguments() -> ETLConfig:
    """Parse command-line arguments into an ETL configuration."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the Aegis-Art-Atelier dataset from OpenBrush-75K "
            "using streaming and per-style reservoir sampling."
        )
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/content/aegis_art_atelier_22k"),
        help="Local directory where the dataset will be generated.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used for reservoir sampling.",
    )
    parser.add_argument(
        "--dry-run",
        type=int,
        default=None,
        help="Stop after streaming the specified number of records.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=2_000,
        help="Progress reporting interval in streamed records.",
    )
    parser.add_argument(
        "--drive-output",
        type=Path,
        default=None,
        help=(
            "Optional Google Drive directory where the final archive "
            "will be copied."
        ),
    )

    args = parser.parse_args()

    return ETLConfig(
        output_dir=args.output_dir,
        seed=args.seed,
        dry_run=args.dry_run,
        log_every=args.log_every,
        drive_output=args.drive_output,
    )


def main() -> None:
    """Run the ETL pipeline from the command line."""
    try:
        config = parse_arguments()
        run_etl(config)

    except KeyboardInterrupt:
        logging.getLogger(LOGGER_NAME).warning(
            "ETL execution interrupted by the user."
        )
        raise SystemExit(130)

    except Exception:
        logging.getLogger(LOGGER_NAME).exception(
            "ETL execution failed."
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()