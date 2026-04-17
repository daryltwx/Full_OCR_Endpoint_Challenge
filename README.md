# Fullerton Health OCR Microservice

A FastAPI microservice that accepts medical documents (PDF/JPG/PNG), classifies them as `referral_letter`, `medical_certificate`, or `receipt`, extracts structured fields, and returns JSON.

## Architecture

```
POST /ocr (multipart file upload)
    |
    v
[File Validation] -- invalid MIME / missing --> 400
    |
    v
[OCR Engine] -- pdf2image + pytesseract --> raw text + page images
    |
    v
[Classifier] -- keyword-based priority rules --> document_type
    |                                              |
    | (unknown)                                    v
    v                                     [Extractor Registry]
   422                                       |       |       |
                                  Referral  MC    Receipt
                                  Letter
                                             |
                                             v
                                    [Structured JSON Response]
```

**Key components:**
- **OCR Engine** (`app/services/ocr_engine.py`): Converts PDFs to images at 300 DPI via `pdf2image`, then extracts text with `pytesseract`
- **Classifier** (`app/services/classifier.py`): Priority-ordered keyword matching (medical_certificate > receipt > referral_letter)
- **Extractors** (`app/services/extractors/`): Regex-based field extraction, one class per document type
- **Signature Detector** (`app/services/signature_detector.py`): OpenCV contour analysis on the lower half of page images — early blob detection for large signature marks, plus multi-stage filtering (extent, text-line rejection, spatial clustering) to distinguish handwriting from printed text and redaction bars
- **Utilities** (`app/utils/`): Date normalisation (to DD/MM/YYYY) and amount parsing (currency string to integer)

## Setup

### Prerequisites
- Python 3.14+
- Tesseract OCR
- Poppler (for PDF to image conversion)

```bash
# macOS
brew install tesseract poppler

# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils
```

### Quick start

```bash
make setup   # create venv and install dependencies
make run     # start the server at http://localhost:8000
```

Or manually:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Usage

### Sample curl commands

```bash
# Referral letter
curl -X POST -F "file=@sample_documents/referral_letter.pdf" http://localhost:8000/ocr

# Medical certificate
curl -X POST -F "file=@sample_documents/medical_certificate.pdf" http://localhost:8000/ocr

# Receipt
curl -X POST -F "file=@sample_documents/receipt.pdf" http://localhost:8000/ocr
```

### Example response

```json
{
  "message": "Processing completed.",
  "result": {
    "document_type": "receipt",
    "total_time": 1.23,
    "finalJson": {
      "claimant_name": "JOHN DOE",
      "claimant_address": "123 SAMPLE ST #01-01",
      "claimant_date_of_birth": null,
      "provider_name": "RafflesMedical",
      "tax_amount": 365,
      "total_amount": 4925
    }
  }
}
```

### Error responses

| Status | Condition | Body |
|--------|-----------|------|
| 400 | Missing file or invalid MIME type | `{"error": "file_missing"}` |
| 422 | Unrecognised document type | `{"error": "unsupported_document_type"}` |
| 500 | Unhandled exception | `{"error": "internal_server_error"}` |

## Run tests

```bash
make test
```

## Extending to new document types

1. **Create an extractor** in `app/services/extractors/` that extends `BaseExtractor`:
   ```python
   from app.services.extractors.base import BaseExtractor

   class MyDocExtractor(BaseExtractor):
       def extract(self, text, images):
           return {"field_name": self._extract_field(text)}
   ```

2. **Register it** in `app/services/extractors/__init__.py`:
   ```python
   from app.services.extractors.my_doc import MyDocExtractor
   EXTRACTOR_REGISTRY["my_doc_type"] = MyDocExtractor
   ```

3. **Add classifier keywords** in `app/services/classifier.py`:
   ```python
   _RULES.append(("my_doc_type", ["keyword1", "keyword2"]))
   ```

## Project structure

```
app/
  main.py                        # FastAPI app, exception handlers
  config.py                      # Settings (DPI, MIME types, thresholds)
  routes/ocr.py                  # POST /ocr endpoint
  services/
    ocr_engine.py                # pdf2image + pytesseract
    classifier.py                # Keyword-based document classification
    signature_detector.py        # OpenCV contour analysis
    extractors/
      __init__.py                # Extractor registry
      base.py                    # Abstract base extractor
      referral_letter.py         # Referral letter field extraction
      medical_certificate.py     # Medical certificate field extraction
      receipt.py                 # Receipt field extraction
  utils/
    amount_parser.py             # "$49.25" -> 4925
    date_parser.py               # "30-Nov-2022" -> "30/11/2022"
tests/                           # Unit + integration tests
sample_documents/                # Sample PDFs for testing
Makefile                         # make setup / run / test / lint / clean
```
