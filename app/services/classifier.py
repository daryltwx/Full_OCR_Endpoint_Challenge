_RULES: list[tuple[str, list[str]]] = [
    (
        "medical_certificate",
        [
            "medical certificate",
            "unfit for duty",
            "outpatient sick leave",
            "type of medical certificate",
        ],
    ),
    (
        "receipt",
        [
            "tax invoice",
            "total amount paid",
            "gst @",
            "sub-total",
            "sub total",
        ],
    ),
    (
        "referral_letter",
        [
            "referral",
            "dear dr",
            "kind regards",
            "thank you for seeing",
        ],
    ),
]


def classify_document(text: str) -> str | None:
    """Classify a document based on keyword matching.

    Args:
        text: OCR-extracted text from the document.

    Returns:
        A document type string (e.g. ``"referral_letter"``), or None
        if no known type matches.
    """
    lower = text.lower()
    for doc_type, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return doc_type
    return None
