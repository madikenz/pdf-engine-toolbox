"""Image extraction and rendering endpoints."""

import time

from fastapi import APIRouter, Depends

from app.dependencies import require_auth
from app.models.requests import ExtractImagesRequest, PageToImageRequest
from app.models.responses import (
    ExtractImagesResponse,
    ExtractImagesData,
    ExtractedImage,
    PageToImageResponse,
    RenderedPage,
)
from app.services import download_service, pdf_service, cache_service

router = APIRouter(prefix="/images")


@router.post(
    "/extract", response_model=ExtractImagesResponse, dependencies=[Depends(require_auth)]
)
async def extract_images(request: ExtractImagesRequest):
    """Extract embedded images from PDF pages."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    images = pdf_service.extract_images(
        pdf_bytes, request.pages, request.min_width, request.min_height, request.format
    )

    elapsed = (time.monotonic() - start) * 1000

    return ExtractImagesResponse(
        success=True,
        data=ExtractImagesData(
            images=[ExtractedImage(**img) for img in images],
            total_count=len(images),
        ),
        processing_time_ms=round(elapsed, 2),
    )


@router.post(
    "/render", response_model=PageToImageResponse, dependencies=[Depends(require_auth)]
)
async def render_page(request: PageToImageRequest):
    """Render a single page as a high-resolution image."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Check cache
    src_hash = cache_service.content_hash(pdf_bytes)
    cache_params = {"page": request.page, "dpi": request.dpi, "format": request.format, "quality": request.quality}
    cached = cache_service.get_cached(src_hash, "render", cache_params)
    if cached and isinstance(cached, dict):
        elapsed = (time.monotonic() - start) * 1000
        return PageToImageResponse(
            success=True,
            data=RenderedPage(**cached),
            processing_time_ms=round(elapsed, 2),
        )

    result = pdf_service.convert_page_to_image(
        pdf_bytes, request.page, request.dpi, request.format, request.quality
    )

    cache_service.put_cached(src_hash, "render", result, cache_params)

    elapsed = (time.monotonic() - start) * 1000

    return PageToImageResponse(
        success=True,
        data=RenderedPage(**result),
        processing_time_ms=round(elapsed, 2),
    )
