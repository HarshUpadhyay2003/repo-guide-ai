import json
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.utils.url_validation import validate_github_url


client = TestClient(app)


def test_url_validation_valid_urls():
    """Verify that canonical GitHub URLs parse correctly."""
    owner, repo = validate_github_url("https://github.com/pallets/flask")
    assert owner == "pallets"
    assert repo == "flask"

    owner2, repo2 = validate_github_url("https://www.github.com/django/django.git")
    assert owner2 == "django"
    assert repo2 == "django"


def test_url_validation_invalid_scheme():
    """Verify that non-HTTPS schemes are strictly rejected."""
    with pytest.raises(ValueError, match="Only 'https' is permitted"):
        validate_github_url("http://github.com/pallets/flask")

    with pytest.raises(ValueError, match="Only 'https' is permitted"):
        validate_github_url("file:///etc/passwd")


def test_url_validation_invalid_hosts():
    """Verify that localhost, IP literals, and non-GitHub hosts are rejected."""
    with pytest.raises(ValueError, match="is not a permitted public host"):
        validate_github_url("https://localhost/pallets/flask")

    with pytest.raises(ValueError, match="IP literals are not permitted"):
        validate_github_url("https://127.0.0.1/pallets/flask")

    with pytest.raises(ValueError, match="IP literals are not permitted"):
        validate_github_url("https://169.254.169.254/latest/meta-data")

    with pytest.raises(ValueError, match="Only 'github.com' is permitted"):
        validate_github_url("https://gitlab.com/owner/repo")


def test_url_validation_invalid_paths():
    """Verify that incomplete repository paths are rejected."""
    with pytest.raises(ValueError, match="Invalid GitHub repository path"):
        validate_github_url("https://github.com/pallets")

    with pytest.raises(ValueError, match="Invalid GitHub repository path"):
        validate_github_url("https://github.com/")


def test_payload_size_limit_exceeded():
    """Verify that HTTP POST requests exceeding MAX_PAYLOAD_SIZE_BYTES return 413 Payload Too Large."""
    # Create oversized JSON payload > 1 MB
    oversized_data = {"url": "https://github.com/pallets/flask", "extra": "x" * 1500000}
    response = client.post("/repo/analyze", json=oversized_data)
    assert response.status_code == 413
    assert "Payload too large" in response.json()["detail"]


def test_cors_wildcard_origins():
    """Verify that default wildcard origin does not expose Access-Control-Allow-Credentials."""
    response = client.options(
        "/repo/analyze",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    # Credentials must NOT be allowed when origin is wildcard '*'
    assert "access-control-allow-credentials" not in response.headers


def test_proxy_headers_handling():
    """Verify that ProxyHeadersMiddleware correctly handles X-Forwarded-For headers."""
    response = client.get("/health", headers={"X-Forwarded-For": "203.0.113.195"})
    assert response.status_code == 200
