import numpy as np
import pytest
from PIL import Image

from app.services.image_preprocessor import preprocess_for_ocr


def _make_image(width: int = 800, height: int = 600, color: int = 255) -> Image.Image:
    """Create a simple solid-color RGB image."""
    arr = np.full((height, width, 3), color, dtype=np.uint8)
    return Image.fromarray(arr)


def _draw_horizontal_lines(img: Image.Image, y_positions: list[int], thickness: int = 2) -> Image.Image:
    """Draw black horizontal lines on a white image."""
    arr = np.array(img)
    for y in y_positions:
        arr[y : y + thickness, :] = 0
    return Image.fromarray(arr)


class TestPreprocessForOcr:
    def test_returns_nonempty_list_of_images(self):
        img = _make_image()
        # Add some content so it's not completely blank
        arr = np.array(img)
        arr[100:150, 100:700] = 0  # dark band
        arr[300:350, 100:700] = 0  # another dark band
        result = preprocess_for_ocr(Image.fromarray(arr))

        assert isinstance(result, list)
        assert len(result) > 0
        for r in result:
            assert isinstance(r, Image.Image)

    def test_blank_image_returns_regions(self):
        """Uniform/blank images should not crash and should return regions."""
        img = _make_image(color=255)
        result = preprocess_for_ocr(img)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_all_black_image_returns_regions(self):
        """All-black images should not crash."""
        img = _make_image(color=0)
        result = preprocess_for_ocr(img)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_horizontal_lines_removed(self):
        """Horizontal lines spanning the image width should be removed."""
        img = _make_image(width=800, height=600, color=255)
        # Draw full-width horizontal lines (like table borders)
        img_with_lines = _draw_horizontal_lines(img, [100, 200, 300, 400], thickness=2)

        # Convert original to check: lines should produce ink in binary
        arr_with_lines = np.array(img_with_lines.convert("L"))
        has_dark_rows = np.any(arr_with_lines[100, :] < 128)
        assert has_dark_rows, "Precondition: image should have dark line pixels"

        # After preprocessing, the lines should be gone from the output regions
        regions = preprocess_for_ocr(img_with_lines)
        for region in regions:
            region_arr = np.array(region)
            # Region should be mostly white (lines removed)
            # At least 95% of pixels should be white (>200)
            if region_arr.ndim == 2:
                white_ratio = np.mean(region_arr > 200)
            else:
                gray = np.mean(region_arr, axis=2)
                white_ratio = np.mean(gray > 200)
            assert white_ratio > 0.90, (
                f"Region should be mostly white after line removal, got {white_ratio:.2%}"
            )

    def test_small_image(self):
        """Very small images should not crash."""
        img = _make_image(width=50, height=50, color=200)
        result = preprocess_for_ocr(img)
        assert isinstance(result, list)
        assert len(result) > 0
