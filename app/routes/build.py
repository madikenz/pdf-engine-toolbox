"""Build (commit) endpoint - assembles final PDF from multiple sources."""

from fastapi import APIRouter, Depends, Response

from app.dependencies import require_auth
from app.models.requests import BuildRequest
from app.services import download_service, pdf_service

router = APIRouter()


@router.post("/build", dependencies=[Depends(require_auth)])
async def build_pdf(request: BuildRequest):
    """Build final PDF from multiple sources with all transformations.

    This is the "commit" operation that:
    1. Merges pages from multiple source PDFs in order
    2. Applies page rotations
    3. Optionally flattens annotations into content
    4. Optionally adds bookmarks
    5. Optionally compresses the result
    """
    # Download all source PDFs
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

    # Prepare annotations for flattening
    annotations = None
    if request.annotations:
        annotations = [a.model_dump() for a in request.annotations]

    # Prepare bookmarks
    bookmarks = None
    if request.bookmarks:
        bookmarks = [b.model_dump() for b in request.bookmarks]

    result = pdf_service.build_pdf(
        sources=sources,
        annotations=annotations,
        flatten=request.flatten_annotations,
        compress=request.compress,
        bookmarks=bookmarks,
    )

    return Response(content=result, media_type="application/pdf")
