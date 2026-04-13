import cv2
import numpy as np
from PIL import Image

from app.config import settings


def detect_signature(images: list[Image.Image], text: str) -> bool:
    """Return True if a handwritten signature is detected in the images."""
    lower = text.lower()
    if "electronically generated" in lower or "no signature" in lower:
        return False

    for pil_img in images:
        if _check_image_for_signature(pil_img):
            return True
    return False


def _check_image_for_signature(pil_img: Image.Image) -> bool:
    img_array = np.array(pil_img)
    h, w = img_array.shape[:2]

    # Crop lower 50% where signatures typically appear
    cropped = img_array[h // 2 :, :]

    gray = cv2.cvtColor(cropped, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    qualifying = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < settings.sig_min_contour_area or area > settings.sig_max_contour_area:
            continue

        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            continue
        solidity = area / hull_area
        if solidity < settings.sig_min_solidity or solidity > settings.sig_max_solidity:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = max(bw, bh) / (min(bw, bh) + 1e-6)
        if aspect > 15:
            continue

        qualifying.append(cnt)

    if len(qualifying) < settings.sig_min_qualifying_contours:
        return False

    # Check spatial clustering — signature strokes are near each other
    centroids = []
    for cnt in qualifying:
        m = cv2.moments(cnt)
        if m["m00"] > 0:
            cx = m["m10"] / m["m00"]
            cy = m["m01"] / m["m00"]
            centroids.append((cx, cy))

    if len(centroids) < settings.sig_min_qualifying_contours:
        return False

    centroids_arr = np.array(centroids)
    median_x = np.median(centroids_arr[:, 0])
    median_y = np.median(centroids_arr[:, 1])

    crop_h, crop_w = cropped.shape[:2]
    radius_x = crop_w * 0.3
    radius_y = crop_h * 0.3

    clustered = sum(
        1
        for cx, cy in centroids
        if abs(cx - median_x) < radius_x and abs(cy - median_y) < radius_y
    )

    return clustered >= settings.sig_min_qualifying_contours
