"""Test repair endpoint."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_repair_pdf(client, auth_headers, sample_pdf_bytes):
    """Repair should return a valid PDF even for a normal file."""
    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/repair", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/repair", content=body, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    # Verify the result is a valid PDF
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 5
