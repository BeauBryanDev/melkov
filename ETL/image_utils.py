import hashlib
import io
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage


class ImageProcessingError(RuntimeError):
    """Raised when an image cannot be loaded or processed."""


def _open_image_source(image_field: Any) -> PILImage:
    """Open an image from a Hugging Face image field.

    The Hugging Face dataset is expected to use ``decode=False``. In that
    configuration, image fields commonly contain either raw bytes or a path.

    Args:
        image_field: Image object, mapping containing ``bytes`` or ``path``,
            byte sequence, or filesystem path.

    Returns:
        An opened PIL image.

    Raises:
        ImageProcessingError: If the image field is missing, malformed, or
            cannot be opened.
    """
    if image_field is None:
        raise ImageProcessingError("The image field is missing.")

    try:
        if isinstance(image_field, Image.Image):
            return image_field

        if isinstance(image_field, Mapping):
            image_bytes = image_field.get("bytes")
            image_path = image_field.get("path")

            if image_bytes is not None:
                return Image.open(io.BytesIO(image_bytes))

            if image_path:
                return Image.open(Path(image_path))

            raise ImageProcessingError(
                "The image mapping contains neither bytes nor path."
            )

        if isinstance(image_field, (bytes, bytearray, memoryview)):
            return Image.open(io.BytesIO(bytes(image_field)))

        if isinstance(image_field, (str, Path)):
            return Image.open(Path(image_field))

    except Exception as exc:
        raise ImageProcessingError(
            f"Unable to open image source: {exc}"
        ) from exc

    raise ImageProcessingError(
        f"Unsupported image field type: {type(image_field).__name__}"
    )


def _prepare_image(image: PILImage, target_size: tuple[int, int]) -> PILImage:
    try:
        working_image = image
        
        if working_image.format == "JPEG":
            working_image.draft("RGB", target_size)

        oriented_image = ImageOps.exif_transpose(working_image)
        rgb_image = oriented_image.convert("RGB")
        rgb_image.thumbnail(target_size, Image.Resampling.LANCZOS)

        if rgb_image.mode != "RGB":
            rgb_image = rgb_image.convert("RGB")

        return rgb_image

    except Exception as exc:
        raise ImageProcessingError(
            f"Unable to preprocess image: {exc}"
        ) from exc
        
        
        
def encode_pil_image(
    image: PILImage,
    target_size: tuple[int, int] = (896, 896),
    jpeg_quality: int = 90,
) -> bytes:
    """Downscale (aspect-ratio preserving) and encode a PIL image as JPEG bytes.

    No padding or cropping is applied: the image is fit within target_size
    while keeping its original aspect ratio, so Qwen2-VL sees dynamic
    resolution rather than a distorted or letterboxed square.

    Args:
        image: Source PIL image.
        target_size: Maximum output dimensions (longest side bound).
        jpeg_quality: JPEG quality from 1 through 100.

    Returns:
        Encoded JPEG bytes.

    Raises:
        ImageProcessingError: If image validation, processing, or encoding
            fails.
        ValueError: If the image configuration is invalid.
    """
    if len(target_size) != 2:
        raise ValueError("target_size must contain width and height.")

    if target_size[0] <= 0 or target_size[1] <= 0:
        raise ValueError("Image dimensions must be greater than zero.")

    if not 1 <= jpeg_quality <= 100:
        raise ValueError("jpeg_quality must be between 1 and 100.")



    processed_image: PILImage | None = None

    try:
        processed_image = _prepare_image(
            image=image,
            target_size=target_size,

        )

        output_buffer = io.BytesIO()
        processed_image.save(
            output_buffer,
            format="JPEG",
            quality=jpeg_quality,
        )
        return output_buffer.getvalue()

    except ImageProcessingError:
        raise
    except Exception as exc:
        raise ImageProcessingError(
            f"Unable to encode image as JPEG: {exc}"
        ) from exc
    finally:
        if processed_image is not None:
            processed_image.close()


def encode_image_field(
    image_field: Any,
    target_size: tuple[int, int] = (896, 896),
    jpeg_quality: int = 90,
) -> bytes:
    """Load an image field and encode it as a standardized JPEG.

    This function is intended to be called only after an example has entered
    the reservoir. It does not decode or process images that are rejected
    before reservoir selection.

    Args:
        image_field: Hugging Face image field or supported image source.
        target_size: Maximum output dimensions (longest side bound).
        jpeg_quality: JPEG quality from 1 through 100.

    Returns:
        JPEG-encoded image bytes.

    Raises:
        ImageProcessingError: If the source is invalid or processing fails.
    """
    opened_image: PILImage | None = None
    should_close_image = not isinstance(image_field, Image.Image)

    try:
        opened_image = _open_image_source(image_field)

        # Force decoding here so corrupted image data is detected while the
        # current record is being processed and can be skipped by the caller.
        opened_image.load()

        return encode_pil_image(
            image=opened_image,
            target_size=target_size,
            jpeg_quality=jpeg_quality,
        )

    except ImageProcessingError:
        raise
    except Exception as exc:
        raise ImageProcessingError(
            f"Unable to process image field: {exc}"
        ) from exc
    finally:
        if should_close_image and opened_image is not None:
            opened_image.close()


def calculate_sha256(data: bytes) -> str:
    """Calculate the SHA256 digest of binary data.

    Args:
        data: Binary content to hash.

    Returns:
        Lowercase hexadecimal SHA256 digest.

    Raises:
        TypeError: If ``data`` is not bytes-like.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like.")

    return hashlib.sha256(bytes(data)).hexdigest()