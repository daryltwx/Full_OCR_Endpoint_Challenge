# Agentic OCR Pipeline — Design Document

## Overview

This document describes the agentic approach to the OCR endpoint, where an LLM (gemma2 via Ollama) replaces the keyword-based classifier and regex-based extractors from the baseline implementation. The pipeline uses four specialised agents, each responsible for a single stage.

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         POST /ocr                                │
│                    multipart/form-data                            │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Agent 1: OCR Engine                             │
│                                                                  │
│  Tool:   Tesseract (pytesseract)                                │
│  Input:  PDF/JPG/PNG file bytes                                  │
│  Output: Raw OCR text + page images                              │
│                                                                  │
│  • PDF → images via pdf2image (300 DPI)                         │
│  • Images → text via pytesseract.image_to_string()              │
│  • Deterministic — no LLM involved                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│               Agent 2: Classifier (LLM)                          │
│                                                                  │
│  Model:  gemma2 (9B) via Ollama                                  │
│  Input:  First 3000 chars of OCR text                            │
│  Output: "referral_letter" | "medical_certificate" | "receipt"   │
│                                                                  │
│  System prompt constrains output to one of the three types       │
│  or "unknown" (→ HTTP 422). Temperature set to 0.0 for          │
│  deterministic classification.                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│               Agent 3: Extractor (LLM)                           │
│                                                                  │
│  Model:  gemma2 (9B) via Ollama                                  │
│  Input:  Document type + first 4000 chars of OCR text            │
│  Output: JSON with extracted fields                              │
│                                                                  │
│  Each document type has a tailored prompt with:                  │
│  • Field names and descriptions                                  │
│  • Extraction hints (e.g. "name is usually in ALL CAPS")        │
│  • Constraint rules (e.g. "must NOT contain Fullerton Health")  │
│                                                                  │
│  The LLM returns raw JSON that may have inconsistent formats    │
│  (e.g. dates as "30-Nov-2022", amounts as "$49.25" or 49.25).  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              Agent 4: Validator (Rule-based)                      │
│                                                                  │
│  Tool:   Python (no LLM)                                         │
│  Input:  Raw JSON from Agent 3 + images + OCR text               │
│  Output: Normalised, schema-compliant JSON                       │
│                                                                  │
│  Responsibilities:                                               │
│  • Date normalisation → DD/MM/YYYY via date_parser               │
│  • Amount normalisation → integer cents via amount_parser         │
│  • Null handling ("null", "N/A", "none" → null)                 │
│  • Provider name validation (reject "Fullerton Health")          │
│  • Signature detection via OpenCV (for referral letters)         │
│  • Fallback logic (e.g. use date_of_mc if submission_date_time  │
│    is garbled by OCR)                                            │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
                    HTTP 200 JSON Response
```

---

## Agent Details

### Agent 1: OCR Engine

| Property | Value |
|----------|-------|
| Type | Deterministic (no LLM) |
| Tool | Tesseract via pytesseract |
| File | `app/services/ocr_engine.py` |

This agent is intentionally not LLM-based. OCR is a well-solved problem where Tesseract (or PaddleOCR) performs reliably. Using an LLM for raw pixel-to-text conversion would be slower and less accurate.

### Agent 2: Classifier

| Property | Value |
|----------|-------|
| Type | LLM agent |
| Model | gemma2 (9B) via Ollama |
| File | `app/services/classifier_agent.py` |
| Temperature | 0.0 |
| Input limit | 3000 characters |

**Prompt design:**
- System prompt constrains output to exactly one of the three document types
- Only the document type string is returned (no explanation)
- Validated against a whitelist — any unrecognised response maps to `None` → HTTP 422

**Why LLM instead of keywords?**
- Handles OCR noise (garbled text, merged words)
- Generalises to unseen document layouts without new keyword rules
- The baseline keyword classifier works but requires manual rule updates for each new format

### Agent 3: Extractor

| Property | Value |
|----------|-------|
| Type | LLM agent |
| Model | gemma2 (9B) via Ollama |
| File | `app/services/extractor_agent.py` |
| Temperature | 0.0 |
| Input limit | 4000 characters |

**Prompt design per document type:**

| Document | Key extraction hints |
|----------|---------------------|
| Referral letter | "provider_name is the clinic from the HEADER, not the doctor's name" |
| Medical certificate | "If DATE field is garbled, use the MC start date instead" |
| Receipt | "claimant_name is near PAY BY, amounts are dollar strings" |

**Why LLM instead of regex?**
- Regex extraction is brittle — a single OCR error (e.g. `PATIENTIDONO.`) breaks the pattern
- The LLM understands context ("JOHN DOE" after "PAY BY" is the patient name, even with noise)
- Adding new document types requires only a new prompt, not new regex patterns

### Agent 4: Validator

| Property | Value |
|----------|-------|
| Type | Rule-based (no LLM) |
| File | `app/services/extractor_agent.py` (`_validate_and_normalise`) |

**Why rule-based instead of LLM?**
- Format normalisation is deterministic — `"30-Nov-2022"` → `"30/11/2022"` always
- Using an LLM for formatting would be wasteful, slow, and potentially inconsistent
- Schema validation must be guaranteed, not probabilistic
- Signature detection uses OpenCV contour analysis — not a language task

**Validation rules:**
| Rule | Example |
|------|---------|
| Date → DD/MM/YYYY | `"30-Nov-2022"` → `"30/11/2022"` |
| Amount → integer cents | `"$49.25"` → `4925` |
| Null normalisation | `"N/A"`, `"null"`, `"none"` → `null` |
| Provider filter | Reject if contains "Fullerton Health" |
| Invalid date rejection | `"40-Nov-2027"` → `null` (day > 31) |
| Submission date fallback | If null, use `date_of_mc` value |

---

## Comparison: Agentic vs Regex Baseline

| Aspect | Regex Baseline | Agentic (LLM) |
|--------|---------------|----------------|
| **Classification** | Keyword matching (priority ordered) | gemma2 semantic understanding |
| **Extraction** | ~200 lines of regex per document type | ~10 line prompt per document type |
| **New document type** | Write regex extractor + keyword rules | Write a prompt + define field schema |
| **OCR noise handling** | Manual fallbacks per known error | LLM reads through noise naturally |
| **Speed (full suite)** | ~3.7 seconds | ~42 seconds |
| **Dependencies** | None beyond Tesseract | Ollama + gemma2 model (5.4GB) |
| **Determinism** | Fully deterministic | Near-deterministic (temp=0.0) |
| **Accuracy** | Identical (all 31 tests pass) | Identical (all 31 tests pass) |

---

## Configuration

All LLM settings are in `app/config.py`:

```python
class Settings(BaseSettings):
    llm_model: str = "gemma2"    # Any Ollama model name
```

To switch models (e.g. for faster inference):
```bash
ollama pull phi3
# Then set LLM_MODEL=phi3 as environment variable, or change config.py
```

---

## File Structure (New/Modified)

```
app/services/
  llm_client.py            # NEW — Ollama client, JSON parsing
  classifier_agent.py       # NEW — LLM-based document classification
  extractor_agent.py        # NEW — LLM extraction + rule-based validation
  classifier.py             # UNCHANGED — still used by unit tests
  extractors/               # UNCHANGED — still used by unit tests
  ocr_engine.py             # UNCHANGED
  signature_detector.py     # UNCHANGED
app/routes/
  ocr.py                    # MODIFIED — imports classifier_agent + extractor_agent
app/config.py               # MODIFIED — added llm_model setting
requirements.txt            # MODIFIED — added ollama
```

---

## Prerequisites

```bash
# Install and start Ollama
brew install ollama
ollama serve                 # in a separate terminal

# Pull the model
ollama pull gemma2

# Install Python dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

---

## Limitations and Future Improvements

1. **Speed** — Each request makes 2 LLM calls (~15-20s total). Could be reduced by combining classification and extraction into a single prompt, at the cost of prompt complexity.

2. **Model dependency** — Requires Ollama running locally with gemma2 downloaded. For production, consider hosting the model on a GPU server or switching to an API (OpenAI, Anthropic).

3. **Non-determinism** — Even at temperature 0.0, LLM outputs can vary slightly between runs. The validator agent mitigates this by enforcing strict output formatting.

4. **Prompt sensitivity** — The extraction quality depends on prompt engineering. The current prompts were tuned for the three sample documents. New document layouts may require prompt adjustments.

5. **No retry mechanism** — If the LLM returns invalid JSON, the validator returns null fields. A production system should retry with a rephrased prompt.
