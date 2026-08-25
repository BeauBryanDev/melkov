
from __future__ import annotations

import json
import logging
import threading
from typing import Final, TypedDict

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from app.config import ART_STYLE_CLASSES_PATH, ART_STYLE_MODEL_PATH
# this is art styles schema no css or html or js
"""
Melkov's style classifier — EfficientNetV2-S fine-tuned, served as ONNX.

Trained in ``Art_Training/Art_Style_Identifier_CNN.ipynb`` on the same
``Aegis-Art-Atelier-22K`` manifests the VLM uses, over 15 style classes, and
exported to a single self-contained ``.onnx``. Inference is CPU-only and does
not import torch: onnxruntime, Pillow and numpy are the whole runtime.
"""

logger = logging.getLogger(__name__)

# Must match Art_Style_Identifier_CNN.ipynb. Do not tune these to taste.
IMAGE_SIZE: Final[int] = 896
IMAGENET_MEAN: Final[np.ndarray] = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD: Final[np.ndarray] = np.array([0.229, 0.224, 0.225], dtype=np.float32)
DEFAULT_TOP_K: Final[int] = 3
# Reported in every response so the UI can name the classifier that answered.
MODEL_NAME: Final[str] = "melkov-art-style-cnn"

# The exported graph's declared input/output names (torch.onnx.export used
# input_names=["image"], output_names=["logits"]).
_INPUT_NAME: Final[str] = "image"
_OUTPUT_NAME: Final[str] = "logits"

_session: ort.InferenceSession | None = None
_classes: list[str] | None = None
# Loading the session reads ~78 MB from disk. FastAPI runs sync endpoints in a
# thread pool, so two concurrent first-requests would otherwise both load it.
_load_lock = threading.Lock()


class StylePrediction(TypedDict):
    """One row of the classification, scored 0–1."""

    label: str
    probability: float


class StyleIdentification(TypedDict):
    """
    The classifier's full answer — the agreed backend/frontend contract.

    Mirrored by ``app/schemas/chat.py :: StyleIdentification``. ``model`` is
    carried so the UI can label which classifier spoke, since a future version
    may answer from different weights.
    """

    model: str
    predictions: list[StylePrediction]
    top_k: int


def _load_resources() -> tuple[ort.InferenceSession, list[str]]:
    """Load the ONNX session and class list once per process.

    Returns:
        The ready session and its index-ordered class names.

    Raises:
        FileNotFoundError: If either artifact is missing from the models
            directory.
        ValueError: If the class list length disagrees with the model's
            output width, which would mislabel every prediction.
    """
    global _session, _classes
    
    if _session is not None and _classes is not None:
        return _session, _classes

    with _load_lock:
        # Re-checked inside the lock: another thread may have loaded already.
        if _session is None or _classes is None:
            
            if not ART_STYLE_MODEL_PATH.is_file():
                
                raise FileNotFoundError(
                    f"Style model not found at {ART_STYLE_MODEL_PATH}."
                )
            if not ART_STYLE_CLASSES_PATH.is_file():
                
                raise FileNotFoundError(
                    f"Style class list not found at {ART_STYLE_CLASSES_PATH}."
                )

            logger.info("Loading style classifier from %s", ART_STYLE_MODEL_PATH)
            
            session = ort.InferenceSession(
                str(ART_STYLE_MODEL_PATH), providers=["CPUExecutionProvider"]
            )
            with ART_STYLE_CLASSES_PATH.open("r", encoding="utf-8") as handle:
                classes = json.load(handle)

            width = session.get_outputs()[0].shape[-1]
            
            if isinstance(width, int) and width != len(classes):
                raise ValueError(
                    f"Class list has {len(classes)} entries but the model "
                    f"outputs {width} logits — the two artifacts do not match."
                )

            _session, _classes = session, classes

    return _session, _classes


def _pad_to_square(image: Image.Image, 
                   fill: tuple[int, int, int] = (0, 0, 0)
                   ) -> Image.Image:
    """
    Letterbox an image to a square on a black ground.

    Padding rather than stretching is deliberate: squashing a canvas distorts
    brushwork and proportion, which are exactly the cues the network reads.

    Args:
        image: The image to pad.
        fill: The padding colour.

    Returns:
        A square image with the original centred.
    """
    width, height = image.size
    side = max(width, height)
    padded = Image.new("RGB", (side, side), fill)
    padded.paste(image, ((side - width) // 2, (side - height) // 2))
    
    return padded


def _preprocess(image: Image.Image) -> np.ndarray:
    """
    Turn a PIL image into the exact tensor the model was trained on.

    Args:
        image: The artwork, any size or aspect ratio.

    Returns:
        A float32 NCHW array of shape ``(1, 3, 896, 896)``.
    """
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = _pad_to_square(image)
    image = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.BILINEAR)

    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD
    
    return array.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax over the last axis."""
    shifted = np.exp(logits - logits.max(axis=-1, keepdims=True))
    
    return shifted / shifted.sum(axis=-1, keepdims=True)


def identify_art_style(
    image: Image.Image, 
    top_k: int = DEFAULT_TOP_K
    ) -> StyleIdentification:
    """Classify the artistic style of a painting.

    Args:
        image: The artwork to classify.
        top_k: How many ranked styles to return.

    Returns:
        The agreed contract dict: ``model``, ``predictions`` (highest
        probability first), and the ``top_k`` actually applied.

    Raises:
        FileNotFoundError: If the model artifacts are missing.
        ValueError: If the artifacts disagree on the number of classes.
    """
    session, classes = _load_resources()

    logits = session.run([_OUTPUT_NAME], {_INPUT_NAME: _preprocess(image)})[0]
    probabilities = _softmax(logits)[0]

    top_k = max(1, min(top_k, len(classes)))
    ranked = np.argsort(probabilities)[::-1][:top_k]

    return StyleIdentification(
        model=MODEL_NAME,
        predictions=[
            StylePrediction(
                label=classes[index],
                probability=round(float(probabilities[index]), 3),
            )
            for index in ranked
        ], #call the class StyleIdentification
        top_k=top_k,
    )
