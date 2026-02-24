"""Test crop, watermark, and page labels endpoints."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_crop_pages_with_margins(client, auth_headers, sample_pdf_bytes):
    """Crop should reduce visible page area when margins are set."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
        "margins": {"top": 72, "right": 72, "bottom": 72, "left": 72},
    })
    headers = auth_headers("POST", "/pages/crop", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/crop", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    page = result_doc[0]
    # CropBox should be smaller than MediaBox
    cropbox = page.cropbox
    mediabox = page.mediabox
    assert cropbox.width < mediabox.width
    assert cropbox.height < mediabox.height


def test_crop_pages_with_cropbox(client, auth_headers, sample_pdf_bytes):
    """Crop should set an explicit crop box."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
        "crop_box": {"x0": 50, "y0": 50, "x1": 400, "y1": 600},
    })
    headers = auth_headers("POST", "/pages/crop", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/crop", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    page = result_doc[0]
    cropbox = page.cropbox
    assert abs(cropbox.x0 - 50) < 1
    assert abs(cropbox.y0 - 50) < 1


def test_watermark(client, auth_headers, sample_pdf_bytes):
    """Watermark should add text to pages (returns valid PDF)."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "text": "DRAFT",
        "pages": [0],
        "font_size": 60,
        "color": "#FF0000",
        "opacity": 0.3,
    })
    headers = auth_headers("POST", "/transform/watermark", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/transform/watermark", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 5
    # Watermark text should be visible in page content
    text = result_doc[0].get_text()
    assert "DRAFT" in text


def test_page_labels(client, auth_headers, sample_pdf_bytes):
    """Page labels should be set on the PDF."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "labels": [
            {"start_page": 0, "prefix": "", "style": "r", "first_page_num": 1},
            {"start_page": 2, "prefix": "", "style": "D", "first_page_num": 1},
        ],
    })
    headers = auth_headers("POST", "/pages/labels", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/labels", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 5
