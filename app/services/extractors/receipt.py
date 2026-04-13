import re
from PIL import Image

from app.services.extractors.base import BaseExtractor
from app.utils.amount_parser import parse_amount
from app.utils.date_parser import parse_date


class ReceiptExtractor(BaseExtractor):
    def extract(self, text: str, images: list[Image.Image]) -> dict:
        return {
            "claimant_name": self._extract_claimant_name(text),
            "claimant_address": self._extract_address(text),
            "claimant_date_of_birth": self._extract_dob(text),
            "provider_name": self._extract_provider(text),
            "tax_amount": self._extract_tax(text),
            "total_amount": self._extract_total(text),
        }

    def _extract_claimant_name(self, text: str) -> str | None:
        # Look for name on lines after "PAY BY" — the name appears on its own line
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(r"PAY\s*BY", line, re.IGNORECASE):
                # Check the next few lines for an all-caps person name
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j].strip()
                    # Remove trailing single chars / noise from OCR
                    candidate = re.sub(r"\s+[a-z.]{1,2}$", "", candidate).strip()
                    # Match two+ uppercase words (person name)
                    if re.match(r"^[A-Z]{2,}(\s+[A-Z]{2,})+$", candidate):
                        return candidate
                break

        # Fallback: find all-caps person names that aren't receipt field headers
        skip_words = {
            "TAX", "INVOICE", "TOTAL", "AMOUNT", "PAID", "DESCRIPTION",
            "CONSULTATION", "PHARMACEUTICAL", "PRACTICE", "COST",
            "CHARGES", "BEFORE", "AFTER", "BALANCE", "DUE", "ROUNDING",
            "ADJUSTMENT", "PAY", "SELF", "VISA", "BILL", "DATE", "VISIT",
            "SUB", "GST", "LESS", "PATIENT", "NORTH", "SINGAPORE",
        }
        for line in lines:
            stripped = line.strip()
            if re.match(r"^[A-Z]{2,}(\s+[A-Z]{2,})+$", stripped):
                words = set(stripped.split())
                if not words.intersection(skip_words) and len(words) <= 5:
                    return stripped

        return None

    def _extract_address(self, text: str) -> str | None:
        # Look for street address pattern (number + street name + unit)
        # Allow optional missing space after digits (PaddleOCR: "123SAMPLE ST")
        m = re.search(
            r"(\d+\s*[A-Z][A-Z\s]+(?:ST|STREET|RD|ROAD|AVE|AVENUE|DR|DRIVE|BLVD|LANE|LN)\s*(?:#\d+[\-\d]*)?)",
            text,
            re.IGNORECASE,
        )
        if m:
            addr = m.group(1).strip()
            # Normalise missing space between digits and letters (e.g. "123SAMPLE" -> "123 SAMPLE")
            addr = re.sub(r"^(\d+)([A-Z])", r"\1 \2", addr)
            return addr

        # Also look for unit number pattern
        m = re.search(r"(\d+\s*\w[\w\s]+#\d+[\-\d]+)", text)
        if m:
            addr = m.group(1).strip()
            addr = re.sub(r"^(\d+)([A-Z])", r"\1 \2", addr)
            return addr

        return None

    def _extract_dob(self, text: str) -> str | None:
        m = re.search(r"(?:DOB|DATE\s*OF\s*BIRTH)\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return parse_date(m.group(1).strip())
        return None

    def _extract_provider(self, text: str) -> str | None:
        lines = text.split("\n")
        for line in lines[:5]:
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if "fullerton health" in lower:
                continue
            # Skip lines that are just numbers, dates, or addresses
            if re.match(r"^[\d\s/\-:]+$", stripped):
                continue
            if re.search(r"\d{6}", stripped):  # postal code line
                continue
            if any(kw in lower for kw in ["your trusted", "partner", "your"]):
                continue
            if len(stripped) <= 3:
                continue
            if any(c.isalpha() for c in stripped):
                return stripped
        return None

    def _extract_tax(self, text: str) -> int | None:
        # GST @ N% on same line followed by amount
        m = re.search(r"GST\s*@\s*\d+\s*%?\s*[:\s]*\$?\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
        if m:
            return parse_amount(m.group(1))

        # PaddleOCR may put "@ N%" and the amount on separate lines, with
        # GST on yet another line. Find "@ N%" and grab the amount from
        # the next line.
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(r"@\s*\d+\s*%", line):
                # The amount is typically the next line
                for j in range(i + 1, min(len(lines), i + 3)):
                    stripped = lines[j].strip()
                    amt_match = re.match(r"^\$?\s*([\d,]+\.\d{2})$", stripped)
                    if amt_match:
                        return parse_amount(amt_match.group(1))
                break

        return None

    def _extract_total(self, text: str) -> int | None:
        # TOTAL AMOUNT PAID followed by amount on same line (may have parentheses)
        m = re.search(
            r"TOTAL\s+AMOUNT\s+PAID\s*[:\s]*\$?\s*(\(?\d[\d,]*\.?\d*\)?)",
            text,
            re.IGNORECASE,
        )
        if m:
            return parse_amount(m.group(1))

        # PaddleOCR may put TOTAL AMOUNT PAID on its own line with the
        # amount on a preceding line (receipt layout reads amounts right-to-left).
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if re.search(r"TOTAL\s+AMOUNT\s+PAID", line, re.IGNORECASE):
                # Search the lines before for a dollar amount (possibly parenthesised)
                for j in range(i - 1, max(i - 4, -1), -1):
                    stripped = lines[j].strip()
                    amt_match = re.match(
                        r"^\$?\s*(\(?\d[\d,]*\.\d{2}\)?)\s*$",
                        stripped,
                    )
                    if amt_match:
                        return parse_amount(amt_match.group(1))
                break

        return None
