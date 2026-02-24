"""Test health endpoint."""


def test_health_check(client):
    """Health endpoint should return OK without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "pymupdf_version" in data
