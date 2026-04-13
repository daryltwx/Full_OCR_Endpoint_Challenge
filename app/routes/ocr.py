import time

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.ocr_engine import run_ocr
from app.services.classifier import classify_document
from app.services.extractors import EXTRACTOR_REGISTRY

router = APIRouter()


@router.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    # Validate MIME type
    if file.content_type not in settings.allowed_mime_types:
        return JSONResponse(status_code=400, content={"error": "file_missing"})

    start = time.time()

    file_bytes = await file.read()

    # OCR
    text, images = run_ocr(file_bytes, file.content_type)

    # Classify
    document_type = classify_document(text)
    if document_type is None:
        return JSONResponse(
            status_code=422, content={"error": "unsupported_document_type"}
        )

    # Extract
    extractor_cls = EXTRACTOR_REGISTRY[document_type]
    extractor = extractor_cls()
    fields = extractor.extract(text, images)

    total_time = round(time.time() - start, 2)

    return {
        "message": "Processing completed.",
        "result": {
            "document_type": document_type,
            "total_time": total_time,
            "finalJson": fields,
        },
    }
