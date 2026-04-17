from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def referral_pdf():
    return SAMPLE_DIR / "referral_letter.pdf"


@pytest.fixture
def medical_cert_pdf():
    return SAMPLE_DIR / "medical_certificate.pdf"


@pytest.fixture
def receipt_pdf():
    return SAMPLE_DIR / "receipt.pdf"
