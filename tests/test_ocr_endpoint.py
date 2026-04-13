import pytest


def test_no_file(client):
    resp = client.post("/ocr")
    assert resp.status_code == 400


def test_invalid_mime(client):
    resp = client.post(
        "/ocr",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "file_missing"


def test_referral_letter(client, referral_pdf):
    with open(referral_pdf, "rb") as f:
        resp = client.post(
            "/ocr",
            files={"file": ("referral_letter.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Processing completed."
    result = data["result"]
    assert result["document_type"] == "referral_letter"
    fields = result["finalJson"]
    assert fields["claimant_name"] == "JOHN DOE"
    assert "Healthway" in fields["provider_name"]
    assert fields["signature_presence"] is True


def test_medical_certificate(client, medical_cert_pdf):
    with open(medical_cert_pdf, "rb") as f:
        resp = client.post(
            "/ocr",
            files={"file": ("medical_certificate.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["document_type"] == "medical_certificate"
    fields = result["finalJson"]
    assert fields["claimant_name"] == "JOHN DOE"
    assert fields["mc_days"] == 1
    assert fields["date_of_mc"] == "30/11/2022"
    assert fields["submission_date_time"] == "30/11/2022"
    assert "Minmed" in (fields["provider_name"] or "")


def test_receipt(client, receipt_pdf):
    with open(receipt_pdf, "rb") as f:
        resp = client.post(
            "/ocr",
            files={"file": ("receipt.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["document_type"] == "receipt"
    fields = result["finalJson"]
    assert fields["claimant_name"] == "JOHN DOE"
    assert fields["total_amount"] == 4925
    assert fields["tax_amount"] == 365
    assert "Raffles" in (fields["provider_name"] or "")
