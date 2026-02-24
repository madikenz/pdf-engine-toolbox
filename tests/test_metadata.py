"""Test metadata endpoints."""

import json
from unittest.mock import patch, AsyncMock


def test_get_metadata(client, auth_headers, sample_pdf_bytes):
    """Get metadata should return document metadata fields."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
    })
    headers = auth_headers("POST", "/metadata/get", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/metadata/get", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], dict)


def test_set_metadata(client, auth_headers, sample_pdf_bytes):
    """Set metadata should update document metadata and return a valid PDF."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "title": "Tax Return 2024",
        "author": "Jane Smith",
        "subject": "Individual Tax Return",
    })
    headers = auth_headers("POST", "/metadata/set", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/metadata/set", content=body, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    # Verify the metadata was set by reading it back
    import fitz
    doc = fitz.open(stream=response.content, filetype="pdf")
    assert doc.metadata["title"] == "Tax Return 2024"
    assert doc.metadata["author"] == "Jane Smith"
