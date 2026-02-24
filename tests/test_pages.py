"""Test page operation endpoints."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_split_pages(client, auth_headers, sample_pdf_bytes):
    """Split should extract specified pages."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "page_ranges": [{"start": 1, "end": 2}],
    })
    headers = auth_headers("POST", "/pages/split", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/split", content=body, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    # Verify the result PDF has 2 pages
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 2


def test_rotate_pages(client, auth_headers, sample_pdf_bytes):
    """Rotate should apply rotation to specified pages."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0, 1],
        "degrees": 90,
    })
    headers = auth_headers("POST", "/pages/rotate", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/rotate", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert result_doc[0].rotation == 90
    assert result_doc[1].rotation == 90
    assert result_doc[2].rotation == 0  # Unaffected page


def test_delete_pages(client, auth_headers, sample_pdf_bytes):
    """Delete should remove specified pages."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages_to_delete": [0, 4],
    })
    headers = auth_headers("POST", "/pages/delete", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/delete", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 3  # 5 - 2 deleted


def test_reorder_pages(client, auth_headers, sample_pdf_bytes):
    """Reorder should rearrange pages."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "new_order": [4, 3, 2, 1, 0],
    })
    headers = auth_headers("POST", "/pages/reorder", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/pages/reorder", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 5
    # First page should now contain "Page 5" text
    text = result_doc[0].get_text()
    assert "Page 5" in text
