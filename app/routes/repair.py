"""Repair endpoint for corrupted PDFs."""

import time

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.dependencies import require_auth
from app.models.requests import RepairRequest
from app.services import download_service, pdf_service

router = APIRouter()


@router.post("/repair", dependencies=[Depends(require_auth)])
async def repair_pdf(request: RepairRequest):
    """Repair a corrupted PDF by re-saving with garbage collection.

    Useful when clients forward PDFs through WhatsApp, email chains, or
    save from iPhones, causing XREF table corruption.
    """
    start = time.monotonic()

    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.repair_pdf(pdf_bytes)

    elapsed = (time.monotonic() - start) * 1000

    return Response(
        content=result,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=repaired.pdf",
            "X-Processing-Time-Ms": f"{elapsed:.2f}",
        },
    )
