import re
from datetime import datetime

_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

# Patterns we recognise (order matters — try most specific first)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # 30-Nov-2022 / 30 Nov 2022
    (re.compile(r"(\d{1,2})[\s\-]([A-Za-z]{3})[\s\-](\d{4})"), "dMY"),
    # 04-JAN-2023
    (re.compile(r"(\d{1,2})[\s\-]([A-Za-z]{3,9})[\s\-](\d{4})"), "dMY"),
    # 12/09/2022  (DD/MM/YYYY)
    (re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})"), "dmy"),
    # 2022/11/30  (YYYY/MM/DD)
    (re.compile(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})"), "Ymd"),
]


def _valid_date(day: str, month: str, year: str) -> bool:
    """Check that day/month/year form a plausible date."""
    try:
        d, m, y = int(day), int(month), int(year)
        return 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2099
    except ValueError:
        return False


def parse_date(raw: str | None) -> str | None:
    """Normalise a date string to DD/MM/YYYY. Returns None on failure."""
    if raw is None:
        return None
    raw = raw.strip()
    for pattern, fmt in _PATTERNS:
        m = pattern.search(raw)
        if not m:
            continue
        try:
            if fmt == "dMY":
                day = m.group(1).zfill(2)
                month = _MONTH_MAP.get(m.group(2)[:3].lower())
                year = m.group(3)
                if month is None:
                    continue
                if not _valid_date(day, month, year):
                    continue
                return f"{day}/{month}/{year}"
            elif fmt == "dmy":
                day = m.group(1).zfill(2)
                month = m.group(2).zfill(2)
                year = m.group(3)
                if not _valid_date(day, month, year):
                    continue
                return f"{day}/{month}/{year}"
            elif fmt == "Ymd":
                year = m.group(1)
                month = m.group(2).zfill(2)
                day = m.group(3).zfill(2)
                if not _valid_date(day, month, year):
                    continue
                return f"{day}/{month}/{year}"
        except (ValueError, IndexError):
            continue
    return None
