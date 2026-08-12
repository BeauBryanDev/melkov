import tempfile
from gradio_client import Client, handle_file
from PIL import Image

from app.config import MELKOV_VLM_SPACE, MELKOV_VLM_API_NAME, HF_TOKEN
from app.utils.image_utils import save_temp_image, resize_max_dim

_client: Client | None = None


def _get_client() -> Client:
    """ Get a singleton instance of the Gradio Client for the MELKOV VLM Space."""
    
    global _client
    
    if _client is None:
        
        _client = Client(MELKOV_VLM_SPACE, hf_token=HF_TOKEN or None)
        
    return _client


def describe_artwork(image: Image.Image) -> str:
    """Send an image to the fine-tuned VLM (Qwen2.5-VL) and return the
    artistic description in a museum style.

    NOTE: Adjust the positional parameter names of .predict()
    according to the actual signature of your Gradio function (check the space's API docs
    at beaunix/melkov).
    """
    image = resize_max_dim(image, max_dim=1024)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        
        save_temp_image(image, tmp.name)
        
        client = _get_client()
        
        result = client.predict(
            
            handle_file(tmp.name),
            api_name=MELKOV_VLM_API_NAME,
        )

    # The result can come as a string directly or as a dict, depending on your Gradio app.
    if isinstance(result, dict) and "description" in result:
        
        return result["description"]
    
    return str(result)
