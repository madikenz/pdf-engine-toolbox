"""Test image-to-PDF conversion endpoint."""

import json
from unittest.mock import patch, AsyncMock

import fitz
from PIL import Image
import io


def _create_test_image(width=400, height=300, color="red", fmt="PNG"):
    """Create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_images_to_pdf(client, auth_headers):
    """Converting images should produce a multi-page PDF."""
    img1 = _create_test_image(400, 300, "red")
    img2 = _create_test_image(600, 400, "blue")

    body = json.dumps({
        "image_urls": [
            "https://example.com/receipt1.png",
            "https://example.com/receipt2.png",
        ],
        "filenames": ["receipt1.png", "receipt2.png"],
    })
    headers = auth_headers("POST", "/convert/from-image", body)

    # Mock download_pdf to return different images for each call
    call_count = {"n": 0}
    images = [img1, img2]

    async def mock_download(url):
        idx = call_count["n"]
        call_count["n"] += 1
        return images[idx]

    with patch(
        "app.services.download_service.download_pdf",
        side_effect=mock_download,
    ):
        response = client.post("/convert/from-image", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 2


def test_single_image_to_pdf(client, auth_headers):
    """Single image should produce a 1-page PDF."""
    img = _create_test_image(500, 500, "green")

    body = json.dumps({
        "image_urls": ["https://example.com/photo.png"],
    })
    headers = auth_headers("POST", "/convert/from-image", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=img,
    ):
        response = client.post("/convert/from-image", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(result_doc) == 1
