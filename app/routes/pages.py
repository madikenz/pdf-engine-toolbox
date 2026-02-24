"""Page operation endpoints: split, merge, rotate, reorder, delete, crop, labels, detect-blank."""

import time

from fastapi import APIRouter, Depends, Response

from app.dependencies import require_auth
from app.models.requests import (
    RotateRequest,
    SplitRequest,
    MergeRequest,
    ReorderRequest,
    DeletePagesRequest,
    CropPagesRequest,
    SetPageLabelsRequest,
    DetectBlankRequest,
)
from app.models.responses import DetectBlankResponse, DetectBlankData, BlankPageInfo
from app.services import download_service, pdf_service, cache_service

router = APIRouter(prefix="/pages")


@router.post("/rotate", dependencies=[Depends(require_auth)])
async def rotate_pages(request: RotateRequest):
    """Rotate specified pages and return modified PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.rotate_pages(pdf_bytes, request.pages, request.degrees)
    return Response(content=result, media_type="application/pdf")


@router.post("/split", dependencies=[Depends(require_auth)])
async def split_pages(request: SplitRequest):
    """Extract page ranges into a new PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Expand page ranges into list of indices
    page_indices = []
    for pr in request.page_ranges:
        page_indices.extend(range(pr.start, pr.end + 1))

    # Convert string-keyed rotations to int-keyed
    rotations = None
    if request.rotations:
        rotations = {int(k): v for k, v in request.rotations.items()}

    result = pdf_service.split_pages(pdf_bytes, page_indices, rotations)
    return Response(content=result, media_type="application/pdf")


@router.post("/merge", dependencies=[Depends(require_auth)])
async def merge_pages(request: MergeRequest):
    """Combine pages from multiple PDFs into one."""
    sources = []
    for src in request.sources:
        src_bytes = await download_service.download_pdf(src.url)
        source_dict = {"bytes": src_bytes}

        if src.pages:
            source_dict["pages"] = [p.model_dump() for p in src.pages]
        elif src.page_ranges:
            source_dict["page_ranges"] = [pr.model_dump() for pr in src.page_ranges]
            if src.rotations:
                source_dict["rotations"] = src.rotations

        sources.append(source_dict)

    result = pdf_service.merge_pdfs(sources)
    return Response(content=result, media_type="application/pdf")


@router.post("/reorder", dependencies=[Depends(require_auth)])
async def reorder_pages(request: ReorderRequest):
    """Reorder pages according to provided order."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.reorder_pages(pdf_bytes, request.new_order)
    return Response(content=result, media_type="application/pdf")


@router.post("/delete", dependencies=[Depends(require_auth)])
async def delete_pages(request: DeletePagesRequest):
    """Remove specified pages from PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.delete_pages(pdf_bytes, request.pages_to_delete)
    return Response(content=result, media_type="application/pdf")


@router.post("/crop", dependencies=[Depends(require_auth)])
async def crop_pages(request: CropPagesRequest):
    """Crop pages by setting margins or an explicit crop box."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    margins = request.margins.model_dump() if request.margins else None
    crop_box = request.crop_box.model_dump() if request.crop_box else None
    result = pdf_service.crop_pages(pdf_bytes, request.pages, margins, crop_box)
    return Response(content=result, media_type="application/pdf")


@router.post("/labels", dependencies=[Depends(require_auth)])
async def set_page_labels(request: SetPageLabelsRequest):
    """Set custom page labels (e.g., roman numerals for front matter)."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    labels = [l.model_dump() for l in request.labels]
    result = pdf_service.set_page_labels(pdf_bytes, labels)
    return Response(content=result, media_type="application/pdf")


@router.post("/detect-blank", response_model=DetectBlankResponse, dependencies=[Depends(require_auth)])
async def detect_blank_pages(request: DetectBlankRequest):
    """Detect blank or nearly-blank pages (from ADF scanning artifacts)."""
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)

    # Check cache
    src_hash = cache_service.content_hash(pdf_bytes)
    cache_params = {"ink_threshold": request.ink_threshold}
    cached = cache_service.get_cached(src_hash, "detect_blank", cache_params)
    if cached and isinstance(cached, list):
        blank_count = sum(1 for p in cached if p["is_blank"])
        elapsed = (time.monotonic() - start) * 1000
        return DetectBlankResponse(
            success=True,
            data=DetectBlankData(
                pages=[BlankPageInfo(**p) for p in cached],
                blank_count=blank_count,
                total_count=len(cached),
            ),
            processing_time_ms=round(elapsed, 2),
        )

    results = pdf_service.detect_blank_pages(pdf_bytes, request.ink_threshold)

    cache_service.put_cached(src_hash, "detect_blank", results, cache_params)

    blank_count = sum(1 for p in results if p["is_blank"])
    elapsed = (time.monotonic() - start) * 1000

    return DetectBlankResponse(
        success=True,
        data=DetectBlankData(
            pages=[BlankPageInfo(**p) for p in results],
            blank_count=blank_count,
            total_count=len(results),
        ),
        processing_time_ms=round(elapsed, 2),
    )
