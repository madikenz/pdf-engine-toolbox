"""Test simple classification endpoint."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def _create_w2_pdf():
    """Create a PDF that looks like a W-2."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(72, 72), "Form W-2 Wage and Tax Statement", fontsize=16)
    page.insert_text(fitz.Point(72, 100), "Employee: John Doe", fontsize=12)
    page.insert_text(fitz.Point(72, 120), "Employer: Acme Corp", fontsize=12)
    return doc.tobytes()


def test_classify_w2(client, auth_headers):
    """Should detect a W-2 form."""
    pdf_bytes = _create_w2_pdf()

    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/classify/simple", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ):
        response = client.post("/classify/simple", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["suggested_label"] == "W-2"
    assert data["data"]["confidence"] > 0
    # tax_year field should be present
    assert "tax_year" in data["data"]


def test_classify_1099_with_tax_year(client, auth_headers, sample_pdf_bytes):
    """Sample PDF contains 'Form 1099-INT' and 'tax year 2024' text."""
    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/classify/simple", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/classify/simple", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["suggested_label"] == "1099-INT"
    # The sample PDF fixture text says "for tax year 2024"
    assert data["data"]["tax_year"] == "2024"


def test_classify_explicit_tax_year(client, auth_headers):
    """Tax Year line on a K-1 form should be extracted."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(72, 72), "Schedule K-1 (Form 1065)", fontsize=16)
    page.insert_text(fitz.Point(72, 100), "Tax Year: 2023", fontsize=12)
    page.insert_text(fitz.Point(72, 120), "Partner's Share of Income", fontsize=12)
    pdf_bytes = doc.tobytes()

    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/classify/simple", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ):
        response = client.post("/classify/simple", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["suggested_label"] == "K-1"
    assert data["data"]["tax_year"] == "2023"


def test_classify_unknown(client, auth_headers):
    """A generic PDF with no tax keywords should return Unknown."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(72, 72), "Hello World - Generic Document", fontsize=16)
    pdf_bytes = doc.tobytes()

    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/classify/simple", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ):
        response = client.post("/classify/simple", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["suggested_label"] == "Unknown"
    assert data["data"]["confidence"] == 0.0
    assert data["data"]["tax_year"] is None
