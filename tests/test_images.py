"""Test image extraction and rendering endpoints."""

import json
from unittest.mock import patch, AsyncMock


def test_render_page(client, auth_headers, sample_pdf_bytes):
    """Render should return a page as a base64 image."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "page": 0,
        "dpi": 72,
        "format": "png",
    })
    headers = auth_headers("POST", "/images/render", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/images/render", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["page_index"] == 0
    assert data["data"]["width"] > 0
    assert data["data"]["height"] > 0
    assert data["data"]["data_url"].startswith("data:image/png;base64,")


def test_extract_images(client, auth_headers, sample_pdf_bytes):
    """Extract images should return image data (sample PDF may have no images)."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
        "min_width": 10,
        "min_height": 10,
    })
    headers = auth_headers("POST", "/images/extract", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/images/extract", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Our sample PDF only has text, so images list should be empty
    assert isinstance(data["data"]["images"], list)
