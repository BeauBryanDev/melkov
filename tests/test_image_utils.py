from __future__ import annotations

import base64

import pytest
from PIL import Image

from app.utils.image_utils import base64_to_pil, pil_to_base64, resize_max_dim


def test_round_trip_preserves_size_and_mode(fake_image: Image.Image) -> None:
    decoded = base64_to_pil(pil_to_base64(fake_image))
    assert decoded.size == fake_image.size
    assert decoded.mode == "RGB"


def test_data_url_prefix_is_stripped(b64_data_url: str, fake_image: Image.Image) -> None:
    assert base64_to_pil(b64_data_url).size == fake_image.size


def test_invalid_attachments_raise_value_error() -> None:
    with pytest.raises(ValueError, match="not valid base64"):
        base64_to_pil("!!!not base64 at all!!!")

    payload = base64.b64encode(b"plain text, no image header").decode()
    with pytest.raises(ValueError, match="not a readable image"):
        base64_to_pil(payload)


def test_resize_max_dim_shrinks_and_never_upscales() -> None:
    wide = Image.new("RGB", (2000, 1000))
    fitted = resize_max_dim(wide, max_dim=1024)
    assert max(fitted.size) == 1024
    assert fitted.size == (1024, 512)

    small = Image.new("RGB", (64, 48))
    assert resize_max_dim(small, max_dim=1024) is small
