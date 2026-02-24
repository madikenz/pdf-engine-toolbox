"""Test transform endpoints."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_compress_pdf(client, auth_headers, sample_pdf_bytes):
    """Compress should return a valid (possibly smaller) PDF."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "quality": "medium",
        "max_image_dpi": 150,
    })
    headers = auth_headers("POST", "/transform/compress", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/transform/compress", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 5  # Same page count


def test_flatten_annotations(client, auth_headers, sample_pdf_bytes):
    """Flatten should burn annotations into PDF."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "annotations": [
            {
                "page_number": 1,
                "type": "stamp",
                "x": 50.0,
                "y": 50.0,
                "stamp_type": "VERIFIED",
                "color": "#4CAF50",
            },
            {
                "page_number": 1,
                "type": "highlight",
                "x": 10.0,
                "y": 15.0,
                "width": 40.0,
                "height": 2.0,
                "color": "#FFEB3B",
            },
        ],
    })
    headers = auth_headers("POST", "/transform/flatten", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/transform/flatten", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    # The stamp text should now be part of the page content
    text = result_doc[0].get_text()
    assert "VERIFIED" in text
