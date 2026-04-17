import cv2
import numpy as np
from PIL import Image

from app.config import settings


def detect_signature(images: list[Image.Image], text: str) -> bool:
    """Detect whether a handwritten signature is present in the images.

    Args:
        images: Page images from the document.
        text: OCR-extracted text (used for early short-circuit keywords).

    Returns:
        True if a handwritten signature is detected, False otherwise.
    """
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

    crop_h, crop_w = cropped.shape[:2]

    # Early check: detect a large handwritten signature blob.
    # Signatures after dilation form a single large, non-rectangular,
    # roughly-square contour above the footer zone.
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10000 or area > 50000:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if y <= 2 or y > crop_h * 0.7:
            continue
        aspect = max(bw, bh) / (min(bw, bh) + 1e-6)
        if aspect >= 2.0:
            continue
        hull_area = cv2.contourArea(cv2.convexHull(cnt))
        if hull_area == 0:
            continue
        solidity = area / hull_area
        if solidity < 0.15 or solidity > 0.90:
            continue
        rect_area = bw * bh
        extent = area / rect_area if rect_area > 0 else 1
        if extent > 0.85:
            continue
        if bw > crop_w * 0.3:
            continue
        return True

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

        # Reject solid filled rectangles (redaction bars)
        rect_area = bw * bh
        if rect_area > 0:
            extent = area / rect_area
            if extent > 0.9:
                continue

        # Reject contours spanning too much of the page width
        if bw > crop_w * 0.4:
            continue

        qualifying.append(cnt)

    # Discard contours touching the crop boundary (text cut by cropping)
    qualifying = [c for c in qualifying if cv2.boundingRect(c)[1] > 2]

    if len(qualifying) < settings.sig_min_qualifying_contours:
        return False

    # Reject uniform contour sizes (printed text, not handwriting)
    areas = np.array([cv2.contourArea(c) for c in qualifying])
    mean_area = np.mean(areas)
    if mean_area > 0:
        cv_areas = np.std(areas) / mean_area
        if cv_areas < 0.3:
            return False

    # Reject text-line patterns: printed text forms horizontal bands,
    # while signature strokes are more randomly distributed vertically.
    cy_list = []
    for cnt in qualifying:
        m = cv2.moments(cnt)
        if m["m00"] > 0:
            cy_list.append(m["m01"] / m["m00"])

    if len(cy_list) < settings.sig_min_qualifying_contours:
        return False

    cy_sorted = sorted(cy_list)
    band_h = crop_h * 0.03  # contours within 3% of crop height = one text line
    text_line_count = 0
    i = 0
    while i < len(cy_sorted):
        j = i + 1
        while j < len(cy_sorted) and cy_sorted[j] - cy_sorted[i] < band_h:
            j += 1
        if j - i >= 3:  # 3+ contours in a thin horizontal band = text line
            text_line_count += j - i
        i = j

    if text_line_count > len(cy_list) * 0.5:
        # Before rejecting, check for a genuine handwritten stroke.
        # Signatures are large, irregular (low solidity), roughly square
        # (aspect < 2), and appear above the footer zone.
        has_signature_stroke = False
        for c in qualifying:
            a = cv2.contourArea(c)
            if a < 10000:
                continue
            hull_a = cv2.contourArea(cv2.convexHull(c))
            if hull_a == 0:
                continue
            sol = a / hull_a
            if sol >= 0.60:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            aspect = max(bw, bh) / (min(bw, bh) + 1e-6)
            if aspect >= 2.0:
                continue
            # Exclude footer zone (bottom 30% of crop)
            if y > crop_h * 0.7:
                continue
            has_signature_stroke = True
            break
        if has_signature_stroke:
            return True
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

    radius_x = crop_w * 0.3
    radius_y = crop_h * 0.3

    clustered = sum(
        1
        for cx, cy in centroids
        if abs(cx - median_x) < radius_x and abs(cy - median_y) < radius_y
    )

    return clustered >= settings.sig_min_qualifying_contours
