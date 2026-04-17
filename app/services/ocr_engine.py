from io import BytesIO

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.config import settings


def run_ocr(
    file_bytes: bytes, content_type: str
) -> tuple[str, list[Image.Image]]:
    """Convert file bytes to OCR text and page images.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        content_type: MIME type (e.g. ``application/pdf``, ``image/png``).

    Returns:
        A tuple of (extracted_text, page_images).
    """
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes, dpi=settings.ocr_dpi)
    else:
        images = [Image.open(BytesIO(file_bytes))]

    text_parts: list[str] = []
    for img in images:
        text_parts.append(pytesseract.image_to_string(img))

    return "\n".join(text_parts), images
