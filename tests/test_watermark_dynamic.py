"""Test dynamic watermark with variable substitution."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_watermark_with_user_name(client, auth_headers, sample_pdf_bytes):
    """Watermark should substitute {user_name} placeholder."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "text": "REVIEWED by {user_name}",
        "pages": [0],
        "font_size": 30,
        "color": "#FF0000",
        "opacity": 0.5,
        "user_name": "John Doe",
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
    # The watermark text should be on the first page
    text = result_doc[0].get_text()
    assert "REVIEWED by John Doe" in text


def test_watermark_with_date(client, auth_headers, sample_pdf_bytes):
    """Watermark should substitute {date} placeholder."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "text": "Draft - {date}",
        "pages": [0],
        "font_size": 40,
        "date": "Feb 4, 2026",
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
    text = result_doc[0].get_text()
    assert "Draft - Feb 4, 2026" in text
