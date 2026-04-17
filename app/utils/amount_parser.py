import re


def parse_amount(raw: str | None) -> int | None:
    """Convert a currency string to an integer in cents.

    Strips all non-digit/non-dot characters, then removes the decimal point.
    Parenthesised amounts like ``(49.25)`` are treated as positive integers.

    Args:
        raw: A currency string (e.g. ``"$49.25"``, ``"(49.25)"``), or None.

    Returns:
        The amount as an integer in cents (e.g. ``4925``), or None on failure.
    """
    if raw is None:
        return None
    # Remove parentheses (used for negative/credit display)
    cleaned = raw.replace("(", "").replace(")", "")
    # Keep only digits and dots
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    if not cleaned:
        return None
    # Remove decimal point to get integer cents
    parts = cleaned.split(".")
    if len(parts) == 2:
        integer_str = parts[0] + parts[1]
    else:
        integer_str = parts[0]
    try:
        return int(integer_str)
    except ValueError:
        return None
