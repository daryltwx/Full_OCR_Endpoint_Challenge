# Approach Comparison: Regex vs Agentic vs PaddleOCR

## Overview

Three approaches were explored for the OCR endpoint. This document compares them across key dimensions to justify the final submission choice.

| Branch | OCR Engine | Classification | Extraction | Status |
|--------|-----------|----------------|------------|--------|
| `01_OCR_test` | Tesseract | Keyword rules | Regex patterns | **Submitted** |
| `02_agentic_ocr` | Tesseract | gemma2 LLM | gemma2 LLM + validator | Explored |
| `03_paddleOCR` | PaddleOCR v5 | Keyword rules | Regex patterns | Explored |

---

## Quick Comparison

| Criteria | Regex + Tesseract | Agentic + Tesseract | Regex + PaddleOCR |
|----------|-------------------|---------------------|-------------------|
| **Test suite time** | ~4 seconds | ~42 seconds | ~2.7 minutes |
| **Single PDF time** | ~1.2 seconds | ~15–20 seconds | ~30–50 seconds |
| **Accuracy** | All 3 docs correct | All 3 docs correct | All 3 docs correct |
| **Setup complexity** | `brew install tesseract` | + Ollama + 5.4GB model | Python ≤3.13 only |
| **Dependencies** | Tesseract (system) | Tesseract + Ollama + gemma2 | Poppler only |
| **Determinism** | 100% deterministic | Near-deterministic (temp=0) | 100% deterministic |
| **Lines of extraction code** | ~200 per doc type | ~10 line prompt per doc type | ~200 per doc type |
| **New doc type effort** | Write regex + keywords | Write a prompt | Write regex + keywords |

---

## Detailed Analysis

### 1. Regex + Tesseract (`01_OCR_test`) — Submitted

**How it works:**
- Tesseract OCR at 300 DPI extracts raw text
- Priority-ordered keyword matching classifies the document
- Regex patterns extract structured fields per document type
- OpenCV contour analysis detects handwritten signatures

**Strengths:**
- Fast — full test suite in 4 seconds
- Zero runtime dependencies beyond Tesseract
- Fully deterministic — identical output every run
- Easy for evaluators to set up and test
- Demonstrates problem-solving through OCR noise workarounds

**Weaknesses:**
- Brittle — regex patterns break when document layout changes
- OCR errors require manual fallback logic (e.g. `40-Nov-2027?` → fallback to MC date)
- Adding a new document type requires writing ~200 lines of regex
- Doesn't generalise to unseen layouts

**Workarounds needed for Tesseract OCR noise:**

| Issue | OCR Output | Fix |
|-------|-----------|-----|
| Garbled date | `40-Nov-2027?` instead of `30-Nov-2022` | Date validation (day ≤ 31) + fallback to MC date |
| Merged text | `PATIENTIDONO.` instead of `PATIENT ID NO.` | Skip PAY BY line, look at next line for name |
| Noisy characters | `CJ Hospitalisation`, `©) Outpatient` | Broader regex matching |

### 2. Agentic + Tesseract (`02_agentic_ocr`) — Explored

**How it works:**
- Same Tesseract OCR for text extraction
- gemma2 (9B) via Ollama classifies the document type
- gemma2 extracts fields using tailored prompts per document type
- Rule-based validator normalises dates, amounts, and enforces schema

**Strengths:**
- Dramatically simpler extraction — prompts replace hundreds of lines of regex
- Handles OCR noise naturally (LLM understands context despite garbled text)
- Adding a new document type = writing a prompt, not regex patterns
- Demonstrates multi-agent system design

**Weaknesses:**
- Slow — 42 seconds for the test suite (10x slower)
- Requires Ollama running + 5.4GB model downloaded
- Near-deterministic but not guaranteed (LLM output can vary)
- Evaluator setup friction — must install Ollama and pull gemma2
- Prompt engineering required — provider_name initially returned doctor's name instead of clinic

**Key design insight:**
The validator agent is deliberately rule-based, not LLM. Format normalisation (`"30-Nov-2022"` → `"30/11/2022"`) is deterministic and must be guaranteed. Using an LLM for formatting would be wasteful and unreliable.

### 3. Regex + PaddleOCR (`03_paddleOCR`) — Explored

**How it works:**
- PaddleOCR (PP-OCRv5) at 150 DPI replaces Tesseract
- Same keyword classifier and regex extractors (adapted for PaddleOCR output format)
- Same OpenCV signature detection

**Strengths:**
- Most accurate OCR — correctly reads `30-Nov-2022` where Tesseract fails
- No system-level OCR install needed (pure Python)
- Lower DPI sufficient (150 vs 300) — PaddleOCR has built-in preprocessing
- Fewer regex workarounds needed

**Weaknesses:**
- Slowest option — 2.7 minutes for the full test suite
- Requires Python ≤ 3.13 (no 3.14 support yet)
- Downloads ~200MB of models on first run
- Higher memory usage (~500MB vs ~50MB)
- PaddleOCR splits text differently — amounts appear on separate lines from labels, requiring different regex patterns

**PaddleOCR-specific extraction changes needed:**

| Issue | PaddleOCR Output | Fix |
|-------|-----------------|-----|
| Split amounts | `GST` / `@ 8%` / `3.65` on 3 lines | Look for `@ N%` then scan next lines for amount |
| Reversed order | `(49.25)` appears before `TOTAL AMOUNT PAID` | Search lines before the label |
| Missing space | `123SAMPLE ST` | Normalise with `re.sub(r"^(\d+)([A-Z])", r"\1 \2")` |

---

## Why Regex + Tesseract Was Submitted

| Factor | Weight | Winner |
|--------|--------|--------|
| Evaluator setup ease | High | Regex + Tesseract |
| Test execution speed | High | Regex + Tesseract (4s) |
| Extraction accuracy | Medium | All identical |
| Code maintainability | Medium | Agentic (less code) |
| Determinism | Medium | Regex + Tesseract |
| OCR accuracy | Low* | PaddleOCR |

*OCR accuracy is low-weight because all three approaches produce correct final results for the sample documents.

**Bottom line:** For a take-home assessment, the evaluator experience matters most. They should be able to:
1. `pip install -r requirements.txt` — works on any Python version
2. `pytest tests/ -v` — passes in 4 seconds
3. `curl -X POST -F "file=@sample.pdf" http://localhost:8000/ocr` — instant response

The agentic approach is the better architecture for production, but the regex approach is the better submission.

---

## Production Recommendation

For Fullerton Health's production system processing thousands of documents daily:

```
Recommended: PaddleOCR + Agentic (LLM) extraction

┌─────────┐    ┌──────────┐    ┌───────────┐    ┌───────────┐
│PaddleOCR│───▶│ LLM      │───▶│ LLM       │───▶│ Rule-based│───▶ JSON
│ (GPU)   │    │Classifier│    │ Extractor  │    │ Validator │
└─────────┘    └──────────┘    └───────────┘    └───────────┘
```

- **PaddleOCR on GPU** — eliminates OCR errors at source, fast inference
- **LLM extraction** — handles new document layouts without code changes
- **Rule-based validation** — guarantees output format compliance
- **Hosted LLM API** (Claude, GPT-4) or self-hosted model for consistent performance
