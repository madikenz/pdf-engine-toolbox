"""Test blank page detection endpoint."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def _create_pdf_with_blank_pages():
    """Create a PDF where pages 0 and 2 have heavy content, page 1 is blank."""
    doc = fitz.open()

    # Page 0: has lots of text (enough ink to be >1%)
    page = doc.new_page(width=612, height=792)
    for y in range(72, 700, 20):
        page.insert_text(fitz.Point(72, y), "This page has lots of content. " * 3, fontsize=12)

    # Page 1: completely blank
    doc.new_page(width=612, height=792)

    # Page 2: has lots of text
    page = doc.new_page(width=612, height=792)
    for y in range(72, 700, 20):
        page.insert_text(fitz.Point(72, y), "Another page with heavy content. " * 3, fontsize=12)

    return doc.tobytes()


def test_detect_blank_pages(client, auth_headers):
    """Should identify the blank page correctly."""
    pdf_bytes = _create_pdf_with_blank_pages()

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "ink_threshold": 0.01,
    })
    headers = auth_headers("POST", "/pages/detect-blank", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ):
        response = client.post("/pages/detect-blank", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_count"] == 3
    assert data["data"]["blank_count"] >= 1

    # Page at index 1 should be blank
    pages = data["data"]["pages"]
    assert pages[1]["is_blank"] is True
    assert pages[0]["is_blank"] is False


def test_detect_blank_all_content(client, auth_headers, sample_pdf_bytes):
    """All pages with content should be detected as non-blank."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
    })
    headers = auth_headers("POST", "/pages/detect-blank", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/detect-blank", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["blank_count"] == 0
