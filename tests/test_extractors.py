from app.services.extractors.medical_certificate import MedicalCertificateExtractor
from app.services.extractors.receipt import ReceiptExtractor


def test_mc_extract_name():
    ext = MedicalCertificateExtractor()
    text = "NAME: JOHN DOE\nNRIC: S1234567A"
    result = ext.extract(text, [])
    assert result["claimant_name"] == "JOHN DOE"


def test_mc_extract_mc_days():
    ext = MedicalCertificateExtractor()
    text = "unfit for duty for a period of 1 days from 30-Nov-2022"
    result = ext.extract(text, [])
    assert result["mc_days"] == 1
    assert result["date_of_mc"] == "30/11/2022"


def test_mc_extract_provider():
    ext = MedicalCertificateExtractor()
    text = "HOSPITAL/CLINIC\n\nMinmed Health Screeners"
    result = ext.extract(text, [])
    assert result["provider_name"] == "Minmed Health Screeners"


def test_mc_submission_date():
    ext = MedicalCertificateExtractor()
    text = "DATE\n30-Nov-2022"
    result = ext.extract(text, [])
    assert result["submission_date_time"] == "30/11/2022"


def test_receipt_extract_total():
    ext = ReceiptExtractor()
    text = "TOTAL AMOUNT PAID  (49.25)"
    result = ext.extract(text, [])
    assert result["total_amount"] == 4925


def test_receipt_extract_tax():
    ext = ReceiptExtractor()
    text = "GST @ 8%   3.65"
    result = ext.extract(text, [])
    assert result["tax_amount"] == 365


def test_receipt_extract_address():
    ext = ReceiptExtractor()
    text = "123 SAMPLE ST #01-01\nDESCRIPTION"
    result = ext.extract(text, [])
    assert result["claimant_address"] == "123 SAMPLE ST #01-01"
