"""Shared test fixtures."""

import hashlib
import hmac
import time

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Generate valid HMAC auth headers for testing."""

    def _make_headers(method: str = "POST", path: str = "/info", body: str = "{}"):
        timestamp = str(int(time.time() * 1000))
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        message = f"{timestamp}:{method}:{path}:{body_hash}"
        signature = hmac.new(
            settings.pdf_engine_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        }

    return _make_headers


@pytest.fixture
def sample_pdf_bytes():
    """Create a simple multi-page test PDF with text content."""
    doc = fitz.open()

    for i in range(5):
        page = doc.new_page(width=612, height=792)
        page.insert_text(
            fitz.Point(72, 72),
            f"Page {i + 1} - Test Content",
            fontsize=24,
            fontname="helv",
        )
        page.insert_text(
            fitz.Point(72, 120),
            f"This is a sample page for testing. SSN: 123-45-{6789 + i}",
            fontsize=12,
            fontname="helv",
        )
        page.insert_text(
            fitz.Point(72, 150),
            f"Form 1099-INT Interest Statement for tax year 2024",
            fontsize=12,
            fontname="helv",
        )

    return doc.tobytes()
