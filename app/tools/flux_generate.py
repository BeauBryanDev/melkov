import random
import requests
from PIL import Image

from app.config import NVIDIA_API_KEY, FLUX_INVOKE_URL
from app.utils.image_utils import base64_to_pil


def generate_artwork(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    seed: int | None = None,
    init_image_b64: str | None = None,
) -> Image.Image:
    """Generate a new artwork from a prompt using the NVIDIA FLUX API.

    Args:
        prompt: The prompt to generate an image from.
        width: The width of the generated image.
        height: The height of the generated image.
        steps: The number of steps to take in the generation process.
        seed: The random seed to use for the generation.
        init_image_b64: Optional initial image to seed the generation.

    Returns:
        The generated image.
    """
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
    }

    payload = {
        "prompt": prompt,
        "image": [init_image_b64] if init_image_b64 else [""],
        "width": width,
        "height": height,
        "seed": seed if seed is not None else random.randint(0, 2**31 - 1),
        "steps": steps,
    }

    response = requests.post(FLUX_INVOKE_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()

    # El campo exacto puede variar (ej: "image", "artifacts", "b64_json") -
    # ajusta esto una vez que veas la respuesta real de la API.
    image_b64 = body.get("image") or body.get("artifacts", [{}])[0].get("base64")
    if not image_b64:
        raise ValueError(f"Respuesta inesperada de FLUX: {body}")

    return base64_to_pil(image_b64)
