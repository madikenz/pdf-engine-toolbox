"""Simple keyword-based document classification."""

import time

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse, ClassifyData
from app.services import download_service, pdf_service, cache_service

router = APIRouter()


@router.post("/classify/simple", response_model=ClassifyResponse, dependencies=[Depends(require_auth)])
async def classify_document(request: ClassifyRequest):
    """Classify a tax document by searching for keywords on the first page.

    Detects common tax forms: W-2, 1099-INT, 1099-DIV, K-1, 1040, etc.
    """
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Check cache
    src_hash = cache_service.content_hash(pdf_bytes)
    cached = cache_service.get_cached(src_hash, "classify")
    if cached and isinstance(cached, dict):
        elapsed = (time.monotonic() - start) * 1000
        return ClassifyResponse(
            success=True,
            data=ClassifyData(**cached),
            processing_time_ms=round(elapsed, 2),
        )

    result = pdf_service.classify_document(pdf_bytes)

    cache_service.put_cached(src_hash, "classify", result)

    elapsed = (time.monotonic() - start) * 1000

    return ClassifyResponse(
        success=True,
        data=ClassifyData(**result),
        processing_time_ms=round(elapsed, 2),
    )
