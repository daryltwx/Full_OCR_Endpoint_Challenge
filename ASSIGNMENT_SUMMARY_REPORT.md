# Assignment Summary Report

**Fullerton Health OCR Endpoint Challenge**
**Candidate:** Daryl Tan

---

## 1. Pipeline Architecture

### 1.1 High-Level Architecture Diagram

```
                          POST /ocr
                     (multipart/form-data)
                             |
                             v
                  +--------------------+
                  |  File Validation   |--- invalid MIME / missing ---> HTTP 400
                  | (MIME type check)  |                            {"error":"file_missing"}
                  +--------------------+
                             |
                             v
                  +--------------------+
                  |    OCR Engine      |
                  | pdf2image (300dpi) |
                  |   + pytesseract    |
                  +--------------------+
                             |
                   raw text + page images
                             |
                             v
                  +--------------------+
                  |    Classifier      |--- unknown type ---> HTTP 422
                  | (keyword priority) |              {"error":"unsupported_document_type"}
                  +--------------------+
                             |
                        document_type
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
    +----------------+ +----------+ +-----------+
    | Referral Letter | | Medical  | |  Receipt  |
    |   Extractor     | |  Cert    | | Extractor |
    |                 | |Extractor | |           |
    +----------------+ +----------+ +-----------+
              |              |              |
              v              v              v
         +---------+
         |Signature|  (referral_letter only)
         |Detector |
         |(OpenCV) |
         +---------+
              |
              +---------- all paths --------+
                             |
                             v
                  +--------------------+
                  |   JSON Response    |
                  |    HTTP 200        |
                  +--------------------+
```

### 1.2 Data Flow Details

| Stage | Component | Input | Output | Technology |
|-------|-----------|-------|--------|------------|
| 1 | File Validation | Multipart upload | Validated bytes + MIME type | FastAPI |
| 2 | OCR Engine | File bytes | Raw text + PIL page images | pdf2image, pytesseract |
| 3 | Classifier | Raw text | `document_type` string | Keyword priority rules |
| 4 | Extractor | Raw text + images | Structured field dict | Regex pattern matching |
| 5 | Signature Detector | Page images + text | Boolean `signature_presence` | OpenCV contour analysis |

### 1.3 Component Design Details

**OCR Engine** (`app/services/ocr_engine.py`)
- Converts PDFs to images at 300 DPI using `pdf2image` (Poppler backend)
- Extracts text from each page using `pytesseract`
- Returns both raw text (for extraction) and original page images (for signature detection)

**Classifier** (`app/services/classifier.py`)
- Priority-ordered keyword matching: `medical_certificate` > `receipt` > `referral_letter`
- Priority ordering prevents misclassification when documents share keywords (e.g., a medical certificate that mentions "receipt")
- Returns `None` for unrecognised types, triggering HTTP 422

**Extractors** (`app/services/extractors/`)
- Registry pattern: a dict mapping `document_type` -> `ExtractorClass`
- Each extractor extends `BaseExtractor` with a single `extract(text, images)` method
- Field extraction uses regex patterns tailored to each document layout
- Utility modules normalise dates to `DD/MM/YYYY` and currency amounts to integers (cents removed)

**Signature Detector** (`app/services/signature_detector.py`)
- Crops lower 50% of each page image (where signatures typically appear)
- Applies adaptive thresholding + morphological dilation
- Finds contours and filters by area, solidity, and aspect ratio
- Checks spatial clustering of qualifying contours to confirm a signature region
- Short-circuits to `false` if text contains "electronically generated" or "no signature"

---

## 2. Design Decisions and Trade-offs

| Decision | Rationale |
|----------|-----------|
| **Tesseract over PaddleOCR** | Simpler dependency chain; sufficient accuracy for structured medical documents with clear printed text |
| **Regex over LLM** | Deterministic, fast (<2s per document), no API costs, no rate limits. Medical documents follow predictable layouts |
| **Keyword classifier over ML** | Three document types with distinct vocabularies; a trained model would be over-engineering for this scope |
| **OpenCV signature detection** | Avoids ML model dependency; contour analysis is robust for handwritten vs. printed distinction |
| **Priority-ordered classification** | Prevents ambiguity when documents share keywords (e.g., MC mentioning "receipt") |
| **Integer amounts (no decimals)** | Per spec requirements; `parse_amount("$49.25")` -> `4925` |

---

## 3. API Results on Assessment Documents

### 3.1 Referral Letter

**Request:**
```bash
curl -X POST -F "file=@sample_documents/referral_letter.pdf" http://localhost:8000/ocr
```

**Response (HTTP 200):**
```json
{
  "message": "Processing completed.",
  "result": {
    "document_type": "referral_letter",
    "total_time": 1.03,
    "finalJson": {
      "claimant_name": "JOHN DOE",
      "provider_name": "Healthway Screening @ Centrepoint",
      "signature_presence": true,
      "total_amount_paid": null,
      "total_approved_amount": null,
      "total_requested_amount": null
    }
  }
}
```

### 3.2 Medical Certificate

**Request:**
```bash
curl -X POST -F "file=@sample_documents/medical_certificate.pdf" http://localhost:8000/ocr
```

**Response (HTTP 200):**
```json
{
  "message": "Processing completed.",
  "result": {
    "document_type": "medical_certificate",
    "total_time": 1.31,
    "finalJson": {
      "claimant_name": "JOHN DOE",
      "claimant_address": null,
      "claimant_date_of_birth": null,
      "diagnosis_name": null,
      "discharge_date_time": null,
      "icd_code": null,
      "provider_name": "Minmed Health Screeners",
      "submission_date_time": "30/11/2022",
      "date_of_mc": "30/11/2022",
      "mc_days": 1
    }
  }
}
```

### 3.3 Receipt

**Request:**
```bash
curl -X POST -F "file=@sample_documents/receipt.pdf" http://localhost:8000/ocr
```

**Response (HTTP 200):**
```json
{
  "message": "Processing completed.",
  "result": {
    "document_type": "receipt",
    "total_time": 1.24,
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

### 3.4 Error Cases

**Missing file (HTTP 400):**
```json
{"error": "file_missing"}
```

**Unsupported document type (HTTP 422):**
```json
{"error": "unsupported_document_type"}
```

---

## 4. Test Results

All **31 tests** pass across 5 test modules:

```
tests/test_amount_parser.py    8 passed   (currency string -> integer conversion)
tests/test_classifier.py       5 passed   (document type classification)
tests/test_date_parser.py      6 passed   (date normalisation to DD/MM/YYYY)
tests/test_extractors.py       7 passed   (field extraction per document type)
tests/test_ocr_endpoint.py     5 passed   (end-to-end API integration tests)
-----------------------------------------------
Total                         31 passed
```

### Test Coverage

| Layer | What is tested |
|-------|---------------|
| **Unit** | Amount parsing (decimals, commas, parentheses, currency symbols), date parsing (multiple formats), individual extractor field extraction |
| **Classification** | Correct type detection for all 3 types, unknown document handling, priority ordering |
| **Integration** | Full POST /ocr pipeline for each sample document, error responses for missing/invalid files |

---

## 5. Limitations and Future Improvements

| Limitation | Potential Improvement |
|------------|----------------------|
| Regex extractors are layout-dependent | Use LLM-based extraction for more flexible parsing |
| Tesseract struggles with table borders | Image preprocessing (line removal) before OCR |
| No support for scanned/rotated documents | Add deskewing and orientation detection |
| Single-page processing assumed | Extend to multi-page document stitching |
| `null` fields for address/DOB on some documents | Data not present in the provided samples; extractors are ready when the data is available |
| Signature detection uses heuristic thresholds | Train a small CNN for more robust detection |

---

## 6. Project Structure

```
app/
  main.py                        # FastAPI app entry point, exception handlers
  config.py                      # Settings (DPI, MIME types, detection thresholds)
  routes/ocr.py                  # POST /ocr endpoint
  services/
    ocr_engine.py                # pdf2image + pytesseract
    classifier.py                # Keyword-based document classification
    signature_detector.py        # OpenCV contour analysis for handwritten signatures
    extractors/
      __init__.py                # Extractor registry (type -> class mapping)
      base.py                    # Abstract base extractor
      referral_letter.py         # Referral letter field extraction
      medical_certificate.py     # Medical certificate field extraction
      receipt.py                 # Receipt field extraction
  utils/
    amount_parser.py             # "$49.25" -> 4925
    date_parser.py               # "30-Nov-2022" -> "30/11/2022"
tests/                           # 31 unit + integration tests
sample_documents/                # 3 sample PDFs for testing
```
