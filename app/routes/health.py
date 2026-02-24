"""Health check endpoint."""

import fitz
from fastapi import APIRouter

from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check - no authentication required."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        pymupdf_version=fitz.version[0],
    )
