"""Security endpoints: encrypt, decrypt, sanitize."""

from fastapi import APIRouter, Depends, Response

from app.dependencies import require_auth
from app.models.requests import EncryptRequest, DecryptRequest, SanitizeRequest
from app.services import download_service, pdf_service

router = APIRouter(prefix="/security")


@router.post("/encrypt", dependencies=[Depends(require_auth)])
async def encrypt_pdf(request: EncryptRequest):
    """Encrypt a PDF with password protection. Returns encrypted PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.encrypt_pdf(
        pdf_bytes, request.user_password, request.owner_password, request.permissions
    )
    return Response(content=result, media_type="application/pdf")


@router.post("/decrypt", dependencies=[Depends(require_auth)])
async def decrypt_pdf(request: DecryptRequest):
    """Decrypt a password-protected PDF. Returns unencrypted PDF."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.decrypt_pdf(pdf_bytes, request.password)
    return Response(content=result, media_type="application/pdf")


@router.post("/sanitize", dependencies=[Depends(require_auth)])
async def sanitize_document(request: SanitizeRequest):
    """Sanitize a PDF by removing metadata, JavaScript, links, and annotations."""
    pdf_bytes = await download_service.download_pdf(request.source_url)
    result = pdf_service.sanitize_document(
        pdf_bytes,
        request.remove_metadata,
        request.remove_javascript,
        request.remove_links,
        request.remove_annotations,
    )
    return Response(content=result, media_type="application/pdf")
