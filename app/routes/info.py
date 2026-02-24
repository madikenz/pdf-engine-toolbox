"""PDF info endpoint."""

import time

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.requests import InfoRequest
from app.models.responses import PdfInfoResponse, PdfInfoData, PageInfo, ErrorDetail
from app.services import download_service, pdf_service

router = APIRouter()


@router.post("/info", response_model=PdfInfoResponse, dependencies=[Depends(require_auth)])
async def get_pdf_info(request: InfoRequest):
    """Get PDF metadata and page information."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    info = pdf_service.get_info(pdf_bytes)

    elapsed = (time.monotonic() - start) * 1000

    return PdfInfoResponse(
        success=True,
        data=PdfInfoData(
            page_count=info["page_count"],
            pages=[PageInfo(**p) for p in info["pages"]],
            is_encrypted=info["is_encrypted"],
            metadata=info["metadata"],
        ),
        processing_time_ms=round(elapsed, 2),
    )
