from app.services.llm_client import query_llm

_SYSTEM = """You are a medical document classifier. You classify documents into exactly one of these types:
- referral_letter
- medical_certificate
- receipt

If the document does not match any type, respond with: unknown

Respond with ONLY the document type string, nothing else."""

_PROMPT_TEMPLATE = """Classify the following OCR text into one of: referral_letter, medical_certificate, receipt, or unknown.

OCR TEXT:
{text}

DOCUMENT TYPE:"""


def classify_document(text: str) -> str | None:
    """Use the LLM to classify a document. Returns the type string or None."""
    # Truncate to avoid overwhelming the model
    truncated = text[:3000]
    response = query_llm(_PROMPT_TEMPLATE.format(text=truncated), system=_SYSTEM)
    result = response.strip().lower().replace('"', "").replace("'", "")

    valid_types = {"referral_letter", "medical_certificate", "receipt"}
    # Check if any valid type is in the response
    for vt in valid_types:
        if vt in result:
            return vt

    return None
