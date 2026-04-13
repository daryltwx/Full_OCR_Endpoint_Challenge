from app.services.classifier import classify_document


def test_medical_certificate():
    text = "This is to certify that the above-named is unfit for duty"
    assert classify_document(text) == "medical_certificate"


def test_receipt():
    text = "TAX INVOICE\nTOTAL AMOUNT PAID  $49.25"
    assert classify_document(text) == "receipt"


def test_referral_letter():
    text = "Dear Dr Smith,\nThank you for seeing the above patient."
    assert classify_document(text) == "referral_letter"


def test_unknown_document():
    text = "This is just some random text with no matching keywords."
    assert classify_document(text) is None


def test_medical_certificate_priority():
    """medical_certificate should win over referral when both keywords present."""
    text = "Dear Dr, this medical certificate is to certify unfit for duty"
    assert classify_document(text) == "medical_certificate"
