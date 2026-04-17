from app.services.extractors.referral_letter import ReferralLetterExtractor
from app.services.extractors.medical_certificate import MedicalCertificateExtractor
from app.services.extractors.receipt import ReceiptExtractor

EXTRACTOR_REGISTRY: dict[str, type] = {
    "referral_letter": ReferralLetterExtractor,
    "medical_certificate": MedicalCertificateExtractor,
    "receipt": ReceiptExtractor,
}
