"""Test redaction endpoints."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_detect_pii(client, auth_headers, sample_pdf_bytes):
    """PII detection should find SSN patterns."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "patterns": ["ssn"],
    })
    headers = auth_headers("POST", "/redact/detect-pii", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/redact/detect-pii", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Our sample PDF contains SSN-like patterns
    assert len(data["data"]["detections"]) > 0
    assert data["data"]["detections"][0]["pattern"] == "ssn"


def test_redact_removes_content(client, auth_headers, sample_pdf_bytes):
    """Redaction should permanently remove text content."""
    # First get text to find a rect
    doc = fitz.open(stream=sample_pdf_bytes, filetype="pdf")
    page = doc[0]
    rects = page.search_for("Test Content")
    assert len(rects) > 0
    r = rects[0]

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "redactions": [{
            "page": 0,
            "rects": [{"x0": r.x0, "y0": r.y0, "x1": r.x1, "y1": r.y1}],
            "fill_color": [0, 0, 0],
        }],
    })
    headers = auth_headers("POST", "/redact", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/redact", content=body, headers=headers)

    assert response.status_code == 200

    # Verify text was removed
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    result_text = result_doc[0].get_text()
    assert "Test Content" not in result_text
