import base64
import io
from PIL import Image


def base64_to_pil(b64_string: str) -> Image.Image:
    """Convert a base64 string to a PIL Image."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
        b64_string = b64_string.encode("utf-8")
        
    raw = base64.b64decode(b64_string)
    
    return Image.open(io.BytesIO(raw)).convert("RGB")


def pil_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """Convert a PIL Image to a base64 string (without data: prefix)."""
    buffer = io.BytesIO()
    
    image.save(buffer, format=fmt)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def save_temp_image(image: Image.Image, path: str) -> str:
    """Save an image to disk, useful for passing a filepath to gradio_client."""
    image.save(path)
    
    return path


def resize_max_dim(image: Image.Image, max_dim: int = 1024) -> Image.Image:
    """Resize an image while maintaining its aspect ratio if it exceeds max_dim in any dimension.
    Useful before sending the image to the VLM or FLUX to avoid large payloads."""
    w, h = image.size
    
    if max(w, h) <= max_dim:
        
        return image
    
    scale = max_dim / max(w, h)
    
    new_size = (int(w * scale), int(h * scale))
    
    return image.resize(new_size, Image.LANCZOS)
