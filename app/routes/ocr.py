import time

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.ocr_engine import run_ocr
from app.services.classifier_agent import classify_document
from app.services.extractor_agent import extract_fields

router = APIRouter()


@router.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    # Validate MIME type
    if file.content_type not in settings.allowed_mime_types:
        return JSONResponse(status_code=400, content={"error": "file_missing"})

    start = time.time()

    file_bytes = await file.read()

    # Agent 1: OCR (Tesseract)
    text, images = run_ocr(file_bytes, file.content_type)

    # Agent 2: Classifier (LLM)
    document_type = classify_document(text)
    if document_type is None:
        return JSONResponse(
            status_code=422, content={"error": "unsupported_document_type"}
        )

    # Agent 3: Extractor (LLM) + Agent 4: Validator (rule-based)
    fields = extract_fields(text, images, document_type)

    total_time = round(time.time() - start, 2)

    return {
        "message": "Processing completed.",
        "result": {
            "document_type": document_type,
            "total_time": total_time,
            "finalJson": fields,
        },
    }
