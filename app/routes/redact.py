"""Redaction endpoints."""

import time

from fastapi import APIRouter, Depends, Response

from app.dependencies import require_auth
from app.models.requests import RedactRequest, DetectPiiRequest
from app.models.responses import (
    DetectPiiResponse,
    DetectPiiData,
    PiiDetection,
    ErrorDetail,
)
from app.services import download_service, pdf_service

router = APIRouter(prefix="/redact")


@router.post("", dependencies=[Depends(require_auth)])
async def apply_redactions(request: RedactRequest):
    """Apply true redactions - permanently remove content."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    redactions = [r.model_dump() for r in request.redactions]
    result = pdf_service.redact_content(pdf_bytes, redactions)
    return Response(content=result, media_type="application/pdf")


@router.post("/detect-pii", response_model=DetectPiiResponse, dependencies=[Depends(require_auth)])
async def detect_pii(request: DetectPiiRequest):
    """Detect PII patterns (SSN, EIN, phone, email) in PDF text."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    detections = pdf_service.detect_pii(pdf_bytes, request.patterns)

    elapsed = (time.monotonic() - start) * 1000

    return DetectPiiResponse(
        success=True,
        data=DetectPiiData(
            detections=[PiiDetection(**d) for d in detections],
        ),
        processing_time_ms=round(elapsed, 2),
    )
