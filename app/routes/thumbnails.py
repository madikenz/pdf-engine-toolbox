"""Thumbnail generation endpoint."""

import time

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.requests import ThumbnailsRequest
from app.models.responses import (
    ThumbnailsResponse,
    ThumbnailsData,
    ThumbnailItem,
)
from app.services import download_service, pdf_service, cache_service

router = APIRouter()


@router.post(
    "/thumbnails", response_model=ThumbnailsResponse, dependencies=[Depends(require_auth)]
)
async def generate_thumbnails(request: ThumbnailsRequest):
    """Generate page thumbnails as base64 data URLs."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Check cache
    src_hash = cache_service.content_hash(pdf_bytes)
    cache_params = {
        "pages": sorted(request.pages) if request.pages else None,
        "width": request.width,
        "format": request.format,
        "quality": request.quality,
    }
    cached = cache_service.get_cached(src_hash, "thumbnails", cache_params)
    if cached and isinstance(cached, list):
        elapsed = (time.monotonic() - start) * 1000
        return ThumbnailsResponse(
            success=True,
            data=ThumbnailsData(thumbnails=[ThumbnailItem(**t) for t in cached]),
            processing_time_ms=round(elapsed, 2),
        )

    thumbnails = pdf_service.generate_thumbnails(
        pdf_bytes, request.pages, request.width, request.format, request.quality
    )

    cache_service.put_cached(src_hash, "thumbnails", thumbnails, cache_params)

    elapsed = (time.monotonic() - start) * 1000

    return ThumbnailsResponse(
        success=True,
        data=ThumbnailsData(
            thumbnails=[ThumbnailItem(**t) for t in thumbnails],
        ),
        processing_time_ms=round(elapsed, 2),
    )
