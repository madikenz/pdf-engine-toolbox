"""Test security endpoints: encrypt, decrypt, sanitize."""

import json
from unittest.mock import patch, AsyncMock

import fitz


def test_encrypt_pdf(client, auth_headers, sample_pdf_bytes):
    """Encrypt should return a password-protected PDF."""
    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "user_password": "user123",
        "owner_password": "owner456",
    })
    headers = auth_headers("POST", "/security/encrypt", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=sample_pdf_bytes,
    ):
        response = client.post("/security/encrypt", content=body, headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    # Verify the PDF is encrypted
    doc = fitz.open(stream=response.content, filetype="pdf")
    assert doc.is_encrypted


def test_decrypt_pdf(client, auth_headers, sample_pdf_bytes):
    """Decrypt should remove password protection."""
    # First encrypt the PDF
    doc = fitz.open(stream=sample_pdf_bytes, filetype="pdf")
    encrypted_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="test123",
        owner_pw="owner456",
    )

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "password": "test123",
    })
    headers = auth_headers("POST", "/security/decrypt", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=encrypted_bytes,
    ):
        response = client.post("/security/decrypt", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert not result_doc.is_encrypted
    assert len(result_doc) == 5


def test_sanitize_removes_metadata(client, auth_headers, sample_pdf_bytes):
    """Sanitize should clear document metadata."""
    # First set some metadata
    doc = fitz.open(stream=sample_pdf_bytes, filetype="pdf")
    doc.set_metadata({"title": "Secret Title", "author": "Secret Author"})
    pdf_with_metadata = doc.tobytes()

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "remove_metadata": True,
        "remove_javascript": True,
    })
    headers = auth_headers("POST", "/security/sanitize", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_with_metadata,
    ):
        response = client.post("/security/sanitize", content=body, headers=headers)

    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert result_doc.metadata["title"] == ""
    assert result_doc.metadata["author"] == ""
