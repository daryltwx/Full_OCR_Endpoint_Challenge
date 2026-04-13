import os
import logging
from io import BytesIO

import numpy as np
from PIL import Image
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR

from app.config import settings

# Suppress noisy PaddleOCR logs
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
logging.getLogger("ppocr").setLevel(logging.WARNING)

_ocr_instance: PaddleOCR | None = None


def _get_ocr() -> PaddleOCR:
    """Lazy-init singleton PaddleOCR to avoid reloading models per request."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = PaddleOCR(use_textline_orientation=True, lang="en")
    return _ocr_instance


def run_ocr(
    file_bytes: bytes, content_type: str
) -> tuple[str, list[Image.Image]]:
    """Convert file bytes to OCR text and page images."""
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes, dpi=settings.ocr_dpi)
    else:
        images = [Image.open(BytesIO(file_bytes))]

    ocr = _get_ocr()
    text_parts: list[str] = []

    for img in images:
        result = ocr.predict(np.array(img))
        page_lines: list[str] = []
        for r in result:
            for txt in r["rec_texts"]:
                page_lines.append(txt)
        text_parts.append("\n".join(page_lines))

    return "\n".join(text_parts), images
