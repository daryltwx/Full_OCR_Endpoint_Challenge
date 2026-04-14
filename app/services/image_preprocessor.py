import cv2
import numpy as np
from PIL import Image

from app.config import settings


def preprocess_for_ocr(pil_img: Image.Image) -> list[Image.Image]:
    """Preprocess an image for cleaner Tesseract OCR.

    Detects table border lines via adaptive thresholding on grayscale,
    then inpaints them on the original RGB image so Tesseract sees
    the same color space as before, minus the interfering lines.
    """
    img_array = np.array(pil_img.convert("RGB"))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    binary = _adaptive_threshold(gray)
    line_mask = _detect_table_lines(binary)

    # Inpaint detected lines — fills with surrounding pixels rather than
    # flat white, which preserves local context for Tesseract
    if np.any(line_mask > 0):
        cleaned = cv2.inpaint(img_array, line_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    else:
        cleaned = img_array

    return [Image.fromarray(cleaned)]


def _adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Gaussian blur + adaptive threshold to produce a clean binary image."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        settings.preprocess_block_size,
        settings.preprocess_constant,
    )
    return binary


def _detect_table_lines(binary: np.ndarray) -> np.ndarray:
    """Detect long horizontal and vertical table lines and return a mask.

    Uses morphological opening with long kernels so only continuous
    lines (not text strokes) are captured.
    """
    h, w = binary.shape

    # Horizontal lines
    horiz_len = max(w // settings.preprocess_line_scale, 1)
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_len, 1))
    horiz_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)

    # Vertical lines
    vert_len = max(h // settings.preprocess_line_scale, 1)
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_len))
    vert_mask = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel)

    line_mask = cv2.bitwise_or(horiz_mask, vert_mask)
    return line_mask
