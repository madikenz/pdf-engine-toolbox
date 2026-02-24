"""PDF Engine Toolbox - FastAPI Application.

PyMuPDF-based PDF processing microservice.
Provides endpoints for page operations, transforms, redaction, text extraction,
thumbnails, and final PDF assembly.

Licensed under AGPL-3.0 (required by PyMuPDF dependency).
"""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.errors import PdfEngineError
from app.routes import (
    health, info, pages, transform, redact, text,
    thumbnails, build, images, metadata, security, annotations,
    repair, convert, classify, tasks,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    log.info("pdf_engine_starting", log_level=settings.log_level)
    yield
    log.info("pdf_engine_shutting_down")


app = FastAPI(
    title="PDF Engine Toolbox",
    description="PyMuPDF-based PDF processing microservice",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(PdfEngineError)
async def pdf_engine_error_handler(request: Request, exc: PdfEngineError):
    """Handle known PDF engine errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.message},
        },
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    log.error("unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        },
    )


# ============================================================================
# Middleware
# ============================================================================


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add X-Processing-Time header to all responses."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed = (time.monotonic() - start) * 1000
    response.headers["X-Processing-Time-Ms"] = f"{elapsed:.2f}"
    return response


# ============================================================================
# Routes
# ============================================================================

app.include_router(health.router, tags=["Health"])
app.include_router(info.router, tags=["Info"])
app.include_router(pages.router, tags=["Pages"])
app.include_router(transform.router, tags=["Transform"])
app.include_router(redact.router, tags=["Redact"])
app.include_router(text.router, tags=["Text"])
app.include_router(thumbnails.router, tags=["Thumbnails"])
app.include_router(build.router, tags=["Build"])
app.include_router(images.router, tags=["Images"])
app.include_router(metadata.router, tags=["Metadata"])
app.include_router(security.router, tags=["Security"])
app.include_router(annotations.router, tags=["Annotations"])
app.include_router(repair.router, tags=["Repair"])
app.include_router(convert.router, tags=["Convert"])
app.include_router(classify.router, tags=["Classify"])
app.include_router(tasks.router, tags=["Tasks"])
