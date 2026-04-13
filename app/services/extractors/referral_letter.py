import re
from PIL import Image

from app.services.extractors.base import BaseExtractor
from app.services.signature_detector import detect_signature
from app.utils.amount_parser import parse_amount


class ReferralLetterExtractor(BaseExtractor):
    def extract(self, text: str, images: list[Image.Image]) -> dict:
        return {
            "claimant_name": self._extract_claimant_name(text),
            "provider_name": self._extract_provider_name(text),
            "signature_presence": detect_signature(images, text),
            "total_amount_paid": None,
            "total_approved_amount": None,
            "total_requested_amount": None,
        }

    def _extract_claimant_name(self, text: str) -> str | None:
        # Look for all-caps name near "ID:" line
        # Pattern: name in caps on a line near ID:
        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Look for a line with ID: that also has caps name nearby
            if re.search(r"\bID\s*:", stripped, re.IGNORECASE):
                # Check if there's a name on this line before "ID:"
                name_match = re.match(r"^([A-Z][A-Z\s]+?)\s*$", stripped)
                if name_match:
                    return name_match.group(1).strip()
                # Check previous lines for all-caps name
                for j in range(max(0, i - 2), i):
                    prev = lines[j].strip()
                    caps_match = re.match(r"^([A-Z][A-Z\s]{2,})$", prev)
                    if caps_match:
                        candidate = caps_match.group(1).strip()
                        # Filter out headers/addresses
                        if len(candidate.split()) <= 5 and "ROAD" not in candidate and "SINGAPORE" not in candidate:
                            return candidate

        # Fallback: look for all-caps name on line with or just before ID:
        m = re.search(r"([A-Z][A-Z\s]{2,})\s*\n?\s*ID\s*:", text)
        if m:
            candidate = m.group(1).strip()
            if len(candidate.split()) <= 5:
                return candidate

        # Fallback: look for JOHN DOE pattern (two+ uppercase words)
        for line in lines:
            stripped = line.strip()
            if re.match(r"^[A-Z]{2,}(\s+[A-Z]{2,})+$", stripped):
                if "SCREENING" not in stripped and "CENTREPOINT" not in stripped and "ROAD" not in stripped:
                    return stripped

        return None

    def _extract_provider_name(self, text: str) -> str | None:
        # The provider is typically the clinic name in the header (first few lines)
        lines = text.split("\n")
        for line in lines[:5]:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip address lines and short lines
            if re.search(r"\d{6}", stripped):  # postal code
                continue
            if len(stripped) < 5:
                continue
            # Check it's not "Fullerton Health"
            if "fullerton health" in stripped.lower():
                continue
            # First substantial non-address line is likely provider name
            if any(c.isalpha() for c in stripped):
                return stripped

        return None
