from PIL import Image

from app.services.llm_client import query_llm_json
from app.services.signature_detector import detect_signature
from app.utils.amount_parser import parse_amount
from app.utils.date_parser import parse_date

_SYSTEM = """You are a medical document data extractor. Extract structured fields from OCR text.
Return ONLY valid JSON with the requested fields. Use null for missing or unreadable values.
Do NOT include any explanation, only the JSON object."""

_SCHEMAS: dict[str, dict] = {
    "referral_letter": {
        "fields": ["claimant_name", "provider_name", "total_amount_paid", "total_approved_amount", "total_requested_amount"],
        "instructions": """Extract these fields from the referral letter:
- claimant_name: The patient's full name (usually in ALL CAPS, near "ID:")
- provider_name: The clinic or healthcare facility name from the HEADER of the letter (the first line, NOT the doctor's name). This is the organisation, not a person. Must NOT contain "Fullerton Health"
- total_amount_paid: Total amount paid as a dollar string (e.g. "$49.25"), or null if not present
- total_approved_amount: Total approved amount as a dollar string, or null if not present
- total_requested_amount: Total requested amount as a dollar string, or null if not present""",
    },
    "medical_certificate": {
        "fields": [
            "claimant_name", "claimant_address", "claimant_date_of_birth",
            "diagnosis_name", "discharge_date_time", "icd_code",
            "provider_name", "submission_date_time", "date_of_mc", "mc_days",
        ],
        "instructions": """Extract these fields from the medical certificate:
- claimant_name: The patient's full name (after "NAME:")
- claimant_address: The patient's address, or null
- claimant_date_of_birth: Date of birth in any format, or null
- diagnosis_name: The diagnosis, or null
- discharge_date_time: Discharge date in any format, or null
- icd_code: ICD code (format like A00.0), or null
- provider_name: Hospital/clinic name. Must NOT contain "Fullerton Health"
- submission_date_time: The date from the DATE field at the bottom. If that date looks garbled or invalid, use the MC start date (the "from" date) instead
- date_of_mc: The MC start date (from "from DD-Mon-YYYY")
- mc_days: Number of MC days as an integer""",
    },
    "receipt": {
        "fields": [
            "claimant_name", "claimant_address", "claimant_date_of_birth",
            "provider_name", "tax_amount", "total_amount",
        ],
        "instructions": """Extract these fields from the receipt:
- claimant_name: The patient's full name (usually in ALL CAPS, near "PAY BY")
- claimant_address: The patient's street address, or null
- claimant_date_of_birth: Date of birth, or null
- provider_name: The clinic/provider name from the header. Must NOT contain "Fullerton Health"
- tax_amount: The GST/tax amount as a dollar string (e.g. "$3.65")
- total_amount: The total amount paid as a dollar string (e.g. "$49.25")""",
    },
}

_PROMPT_TEMPLATE = """Given the following OCR text from a {doc_type} document, extract the requested fields.

{instructions}

OCR TEXT:
{text}

Return ONLY a JSON object with the fields above. Use null for any field you cannot find."""


def extract_fields(text: str, images: list[Image.Image], document_type: str) -> dict:
    """Use the LLM to extract fields, then validate/normalise with rules."""
    schema = _SCHEMAS[document_type]

    prompt = _PROMPT_TEMPLATE.format(
        doc_type=document_type.replace("_", " "),
        instructions=schema["instructions"],
        text=text[:4000],
    )

    raw = query_llm_json(prompt, system=_SYSTEM)
    if raw is None:
        raw = {}

    # Post-process with the validator agent (rule-based)
    return _validate_and_normalise(raw, document_type, text, images)


def _validate_and_normalise(
    raw: dict, document_type: str, text: str, images: list[Image.Image]
) -> dict:
    """Validate LLM output and normalise field formats."""

    if document_type == "referral_letter":
        return {
            "claimant_name": _clean_string(raw.get("claimant_name")),
            "provider_name": _clean_provider(raw.get("provider_name")),
            "signature_presence": detect_signature(images, text),
            "total_amount_paid": _normalise_amount(raw.get("total_amount_paid")),
            "total_approved_amount": _normalise_amount(raw.get("total_approved_amount")),
            "total_requested_amount": _normalise_amount(raw.get("total_requested_amount")),
        }

    elif document_type == "medical_certificate":
        mc_days = raw.get("mc_days")
        if isinstance(mc_days, str):
            try:
                mc_days = int(mc_days)
            except (ValueError, TypeError):
                mc_days = None

        date_of_mc = _normalise_date(raw.get("date_of_mc"))
        submission_dt = _normalise_date(raw.get("submission_date_time"))
        # Fallback: if submission_date_time is garbled, use date_of_mc
        if submission_dt is None and date_of_mc is not None:
            submission_dt = date_of_mc

        return {
            "claimant_name": _clean_string(raw.get("claimant_name")),
            "claimant_address": _clean_string(raw.get("claimant_address")),
            "claimant_date_of_birth": _normalise_date(raw.get("claimant_date_of_birth")),
            "diagnosis_name": _clean_string(raw.get("diagnosis_name")),
            "discharge_date_time": _normalise_date(raw.get("discharge_date_time")),
            "icd_code": _clean_string(raw.get("icd_code")),
            "provider_name": _clean_provider(raw.get("provider_name")),
            "submission_date_time": submission_dt,
            "date_of_mc": date_of_mc,
            "mc_days": mc_days,
        }

    elif document_type == "receipt":
        return {
            "claimant_name": _clean_string(raw.get("claimant_name")),
            "claimant_address": _clean_string(raw.get("claimant_address")),
            "claimant_date_of_birth": _normalise_date(raw.get("claimant_date_of_birth")),
            "provider_name": _clean_provider(raw.get("provider_name")),
            "tax_amount": _normalise_amount(raw.get("tax_amount")),
            "total_amount": _normalise_amount(raw.get("total_amount")),
        }

    return raw


def _clean_string(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "n/a", "na"):
        return None
    return s


def _clean_provider(val) -> str | None:
    s = _clean_string(val)
    if s and "fullerton health" in s.lower():
        return None
    return s


def _normalise_date(val) -> str | None:
    s = _clean_string(val)
    if s is None:
        return None
    parsed = parse_date(s)
    return parsed


def _normalise_amount(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(round(val * 100))
    return parse_amount(str(val))
