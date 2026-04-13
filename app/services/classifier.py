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
    """Return the document type string or None if unrecognised."""
    lower = text.lower()
    for doc_type, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return doc_type
    return None
