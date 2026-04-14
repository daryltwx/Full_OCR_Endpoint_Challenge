from io import BytesIO

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.config import settings
from app.services.image_preprocessor import preprocess_for_ocr


def run_ocr(
    file_bytes: bytes, content_type: str
) -> tuple[str, list[Image.Image]]:
    """Convert file bytes to OCR text and page images.

    Returns original images (not preprocessed) so that downstream
    consumers like the signature detector receive unmodified images.
    """
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes, dpi=settings.ocr_dpi)
    else:
        images = [Image.open(BytesIO(file_bytes))]

    text_parts: list[str] = []
    for img in images:
        if settings.preprocess_enabled:
            regions = preprocess_for_ocr(img)
            region_texts = [pytesseract.image_to_string(r) for r in regions]
            text_parts.append("\n".join(region_texts))
        else:
            text_parts.append(pytesseract.image_to_string(img))

    return "\n".join(text_parts), images
