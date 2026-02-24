"""Test PDF info endpoint."""

from unittest.mock import patch, AsyncMock


def test_info_requires_auth(client):
    """Info endpoint should require authentication."""
    response = client.post("/info", json={"source_url": "https://example.com/test.pdf"})
    assert response.status_code == 401


def test_info_returns_page_data(client, auth_headers, sample_pdf_bytes):
    """Info endpoint should return page count and metadata."""
    import json

    body = json.dumps({"source_url": "https://example.com/test.pdf"})
    headers = auth_headers("POST", "/info", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/info", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["page_count"] == 5
    assert len(data["data"]["pages"]) == 5
    assert data["data"]["pages"][0]["index"] == 0
    assert data["data"]["pages"][0]["has_text"] is True
