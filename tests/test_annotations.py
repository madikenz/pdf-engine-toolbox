"""Test annotation reading endpoint."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_read_annotations(client, auth_headers, sample_pdf_bytes):
    """Read annotations should return existing PDF annotations."""
    # Create a PDF with an annotation
    doc = fitz.open(stream=sample_pdf_bytes, filetype="pdf")
    page = doc[0]
    annot = page.add_text_annot(fitz.Point(100, 100), "Test note")
    pdf_with_annot = doc.tobytes()

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
    })
    headers = auth_headers("POST", "/annotations/read", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_with_annot,
    ):
        response = client.post("/annotations/read", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_count"] >= 1
    assert data["data"]["annotations"][0]["page_index"] == 0


def test_read_annotations_empty(client, auth_headers, sample_pdf_bytes):
    """Read annotations on a PDF with no annotations should return empty list."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
    })
    headers = auth_headers("POST", "/annotations/read", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/annotations/read", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_count"] == 0
