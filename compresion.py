from __future__ import annotations

import logging
import shutil
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CompressionResult:
    """Result of dataset compression.

    Attributes:
        archive_path: Path to the generated tar.gz archive.
        archive_size_bytes: Archive size in bytes.
        elapsed_seconds: Compression duration in seconds.
        drive_copy_path: Optional path of the copied archive.
    """

    archive_path: Path
    archive_size_bytes: int
    elapsed_seconds: float
    drive_copy_path: Path | None = None


def _format_size(size_bytes: int) -> str:
    """Format a byte count using a human-readable unit."""
    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.2f} KB"

    if size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.2f} MB"

    return f"{size_bytes / (1024**3):.2f} GB"


def _archive_filter(
    archive_member_to_exclude: str | None,
):
    """Create a tar filter that optionally excludes one archive member."""

    def filter_member(tar_info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        """Exclude the output archive if it is inside the source directory."""
        if (
            archive_member_to_exclude is not None
            and tar_info.name == archive_member_to_exclude
        ):
            return None

        return tar_info

    return filter_member


def compress_dataset(
    output_dir: Path,
    archive_path: Path,
    logger: logging.Logger | None = None,
) -> CompressionResult:
    """Compress a dataset directory into a gzip-compressed tar archive.

    The archive contains the dataset directory as its top-level member. For
    example, an output directory named ``Aegis-Art-Atelier-22K`` is stored as:

    ``Aegis-Art-Atelier-22K/...``

    Args:
        output_dir: Dataset directory to compress.
        archive_path: Destination tar.gz path.
        logger: Optional logger for progress and completion messages.

    Returns:
        Compression result containing archive metadata.

    Raises:
        FileNotFoundError: If the dataset directory does not exist.
        NotADirectoryError: If output_dir is not a directory.
        OSError: If the archive cannot be written.
    """
    active_logger = logger or logging.getLogger(__name__)
    output_dir = Path(output_dir)
    archive_path = Path(archive_path)

    if not output_dir.exists():
        raise FileNotFoundError(
            f"Dataset directory does not exist: {output_dir}"
        )

    if not output_dir.is_dir():
        raise NotADirectoryError(
            f"Dataset output path is not a directory: {output_dir}"
        )

    archive_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_output_dir = output_dir.resolve()
    resolved_archive_path = archive_path.resolve()

    archive_member_to_exclude: str | None = None

    try:
        archive_relative_path = resolved_archive_path.relative_to(
            resolved_output_dir
        )
        archive_member_to_exclude = (
            f"{output_dir.name}/{archive_relative_path.as_posix()}"
        )
    except ValueError:
        # The archive is outside the dataset directory and cannot be included
        # in the source tree being compressed.
        archive_member_to_exclude = None

    temporary_archive_path = archive_path.with_name(
        f"{archive_path.name}.tmp"
    )

    if temporary_archive_path.exists():
        temporary_archive_path.unlink()

    if archive_path.exists():
        active_logger.warning(
            "Existing archive will be replaced: %s",
            archive_path,
        )

    active_logger.info(
        "Compressing dataset directory %s into %s",
        output_dir,
        archive_path,
    )

    start_time = time.monotonic()

    try:
        with tarfile.open(temporary_archive_path, mode="w:gz") as archive:
            archive.add(
                output_dir,
                arcname=output_dir.name,
                recursive=True,
                filter=_archive_filter(archive_member_to_exclude),
            )

        temporary_archive_path.replace(archive_path)

    except Exception:
        if temporary_archive_path.exists():
            temporary_archive_path.unlink()
        raise

    elapsed_seconds = time.monotonic() - start_time
    archive_size_bytes = archive_path.stat().st_size

    active_logger.info(
        "Compression completed in %.2f seconds. Archive size: %s",
        elapsed_seconds,
        _format_size(archive_size_bytes),
    )

    return CompressionResult(
        archive_path=archive_path,
        archive_size_bytes=archive_size_bytes,
        elapsed_seconds=elapsed_seconds,
    )


def copy_archive_to_directory(
    archive_path: Path,
    destination_dir: Path,
    logger: logging.Logger | None = None,
) -> Path:
    """Copy an archive to an optional destination directory.

    This supports Google Drive paths mounted in Google Colab, such as
    ``/content/drive/MyDrive/...``.

    Args:
        archive_path: Existing archive to copy.
        destination_dir: Destination directory.
        logger: Optional logger for copy progress.

    Returns:
        Destination path of the copied archive.

    Raises:
        FileNotFoundError: If the source archive does not exist.
        IsADirectoryError: If the source archive path is a directory.
        OSError: If copying fails.
    """
    active_logger = logger or logging.getLogger(__name__)
    archive_path = Path(archive_path)
    destination_dir = Path(destination_dir)

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive does not exist: {archive_path}"
        )

    if archive_path.is_dir():
        raise IsADirectoryError(
            f"Archive path is a directory: {archive_path}"
        )

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / archive_path.name

    active_logger.info(
        "Copying archive %s to %s",
        archive_path,
        destination_path,
    )

    shutil.copy2(archive_path, destination_path)

    active_logger.info(
        "Archive copy completed: %s",
        destination_path,
    )

    return destination_path