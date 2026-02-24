"""Test thumbnail WebP format and quality parameter."""

import json
from unittest.mock import patch, AsyncMock


def test_thumbnails_webp_format(client, auth_headers, sample_pdf_bytes):
    """Thumbnails should support WebP format (smaller than PNG)."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
        "width": 200,
        "format": "webp",
        "quality": 80,
    })
    headers = auth_headers("POST", "/thumbnails", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/thumbnails", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["thumbnails"]) == 1
    # WebP data URL should start with the correct MIME type
    assert data["data"]["thumbnails"][0]["data_url"].startswith("data:image/webp;base64,")


def test_thumbnails_default_webp(client, auth_headers, sample_pdf_bytes):
    """Default format should now be WebP."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
    })
    headers = auth_headers("POST", "/thumbnails", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/thumbnails", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    thumb = data["data"]["thumbnails"][0]
    assert thumb["data_url"].startswith("data:image/webp;base64,")


def test_render_webp_format(client, auth_headers, sample_pdf_bytes):
    """Image render should support WebP format."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "page": 0,
        "dpi": 72,
        "format": "webp",
        "quality": 70,
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
    assert data["data"]["data_url"].startswith("data:image/webp;base64,")
