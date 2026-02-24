"""Metadata endpoints."""

import time

from fastapi import APIRouter, Depends, Response

from app.dependencies import require_auth
from app.models.requests import SetMetadataRequest, GetMetadataRequest
from app.models.responses import MetadataResponse
from app.services import download_service, pdf_service

router = APIRouter(prefix="/metadata")


@router.post("/get", response_model=MetadataResponse, dependencies=[Depends(require_auth)])
async def get_metadata(request: GetMetadataRequest):
    """Get all PDF metadata fields."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    metadata = pdf_service.get_metadata(pdf_bytes)

    elapsed = (time.monotonic() - start) * 1000

    return MetadataResponse(
        success=True,
        data=metadata,
        processing_time_ms=round(elapsed, 2),
    )


@router.post("/set", dependencies=[Depends(require_auth)])
async def set_metadata(request: SetMetadataRequest):
    """Set or update PDF metadata fields. Returns modified PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Build metadata dict from provided fields
    metadata = {}
    for key in ("title", "author", "subject", "keywords", "creator", "producer"):
        value = getattr(request, key, None)
        if value is not None:
            metadata[key] = value

    result = pdf_service.set_metadata(pdf_bytes, metadata)
    return Response(content=result, media_type="application/pdf")
