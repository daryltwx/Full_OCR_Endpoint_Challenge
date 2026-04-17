import re
from PIL import Image

from app.services.extractors.base import BaseExtractor
from app.utils.date_parser import parse_date


class MedicalCertificateExtractor(BaseExtractor):
    def extract(self, text: str, images: list[Image.Image]) -> dict:
        return {
            "claimant_name": self._extract_name(text),
            "claimant_address": self._extract_address(text),
            "claimant_date_of_birth": self._extract_dob(text),
            "diagnosis_name": self._extract_diagnosis(text),
            "discharge_date_time": self._extract_discharge(text),
            "icd_code": self._extract_icd(text),
            "provider_name": self._extract_provider(text),
            "submission_date_time": self._extract_submission_date(text),
            "date_of_mc": self._extract_date_of_mc(text),
            "mc_days": self._extract_mc_days(text),
        }

    def _extract_name(self, text: str) -> str | None:
        m = re.search(r"NAME\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _extract_address(self, text: str) -> str | None:
        m = re.search(r"ADDRESS\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _extract_dob(self, text: str) -> str | None:
        m = re.search(r"(?:DOB|DATE\s*OF\s*BIRTH)\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return parse_date(m.group(1).strip())
        return None

    def _extract_diagnosis(self, text: str) -> str | None:
        m = re.search(r"DIAGNOSIS\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _extract_discharge(self, text: str) -> str | None:
        m = re.search(r"Discharged?\s*(?:on)?\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            # Skip if it's just a blank/line
            if raw and not re.match(r"^[\s_\-]+$", raw):
                return parse_date(raw)
        return None

    def _extract_icd(self, text: str) -> str | None:
        m = re.search(r"\b([A-Z]\d{2}(?:\.\d{1,4})?)\b", text)
        if m:
            code = m.group(1)
            # Validate it looks like an ICD code (not an ID like S1234567A)
            if re.match(r"^[A-TV-Z]\d{2}", code):
                return code
        return None

    def _extract_provider(self, text: str) -> str | None:
        # Look for HOSPITAL/CLINIC section header, then scan following lines
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(r"HOSPITAL\s*/?\s*CLINIC", line, re.IGNORECASE):
                # Scan lines after the header for a provider name
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j].strip()
                    if not candidate or candidate.upper() in ("NA", "N/A", "-"):
                        continue
                    if re.match(r"^(DATE|WARD|NAME|COMMENTS)\b", candidate, re.IGNORECASE):
                        continue
                    if re.match(r"^\d", candidate):
                        continue
                    if "fullerton health" in candidate.lower():
                        continue
                    return candidate
                break

        # Fallback: look for known clinic names anywhere in text
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if any(kw in lower for kw in ["minmed", "raffles", "parkway"]):
                if "fullerton health" not in lower and len(stripped) > 3:
                    return stripped

        return None

    def _extract_submission_date(self, text: str) -> str | None:
        # OCR may garble the DATE field in the bottom table, so prefer the
        # date that already appears correctly in the MC body (e.g. "from 30-Nov-2022").
        # Use that as the submission date if the explicit DATE field is unreadable.

        # Try explicit DATE field first
        m = re.search(r"\bDATE\b[:\s]*\n?\s*(\d{1,2}[\s\-][A-Za-z]{3}[\s\-]\d{4})", text)
        if m:
            parsed = parse_date(m.group(1).strip())
            if parsed:
                return parsed

        # Fallback: use the "from DD-Mon-YYYY" date (same as date_of_mc)
        m = re.search(r"from\s+(\d{1,2}[\s\-][A-Za-z]{3}[\s\-]\d{4})", text, re.IGNORECASE)
        if m:
            return parse_date(m.group(1))

        return None

    def _extract_date_of_mc(self, text: str) -> str | None:
        # "from 30-Nov-2022" pattern
        m = re.search(r"from\s+(\d{1,2}[\s\-][A-Za-z]{3}[\s\-]\d{4})", text, re.IGNORECASE)
        if m:
            return parse_date(m.group(1))

        return None

    def _extract_mc_days(self, text: str) -> int | None:
        # "period of N days"
        m = re.search(r"period\s+of\s+(\d+)\s*days?", text, re.IGNORECASE)
        if m:
            return int(m.group(1))

        # "N days" near "unfit for duty"
        m = re.search(r"unfit\s+for\s+duty\s+for\s+a\s+period\s+of\s+(\d+)\s*days?", text, re.IGNORECASE)
        if m:
            return int(m.group(1))

        return None
