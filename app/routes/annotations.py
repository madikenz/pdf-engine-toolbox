"""Annotation reading endpoint."""

import time

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.requests import ReadAnnotationsRequest
from app.models.responses import (
    ReadAnnotationsResponse,
    ReadAnnotationsData,
    AnnotationInfo,
)
from app.services import download_service, pdf_service

router = APIRouter(prefix="/annotations")


@router.post(
    "/read", response_model=ReadAnnotationsResponse, dependencies=[Depends(require_auth)]
)
async def read_annotations(request: ReadAnnotationsRequest):
    """Read existing PDF annotations from pages."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    annotations = pdf_service.read_annotations(pdf_bytes, request.pages)

    elapsed = (time.monotonic() - start) * 1000

    return ReadAnnotationsResponse(
        success=True,
        data=ReadAnnotationsData(
            annotations=[AnnotationInfo(**a) for a in annotations],
            total_count=len(annotations),
        ),
        processing_time_ms=round(elapsed, 2),
    )
