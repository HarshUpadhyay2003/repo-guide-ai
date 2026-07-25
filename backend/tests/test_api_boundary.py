import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.middleware.body_size_limit import BodySizeLimitMiddleware
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


def test_body_size_limit_normal_post_request():
    """Test A: Verify normal POST request reaches endpoint with complete body and returns HTTP 200."""
    response = client.post("/repo/analyze", json={"url": "https://github.com/pallets/flask"})
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "summary" in data


def test_get_cached_repository_analysis():
    """Verify that GET /repo/analysis returns cached snapshot or 404 when missing."""
    # First analyze repo to populate cache
    client.post("/repo/analyze", json={"url": "https://github.com/pallets/flask"})

    # Fetch from GET /repo/analysis
    res = client.get("/repo/analysis?owner=pallets&repo=flask")
    assert res.status_code == 200
    assert "metadata" in res.json()

    # Query uncached repo
    res_missing = client.get("/repo/analysis?owner=unknownowner&repo=unknownrepo")
    assert res_missing.status_code == 404


def test_get_contribution_pdf_with_issue_number():
    """Verify that GET /pdf/contribution accepts optional issue_number parameter."""
    client.post("/repo/analyze", json={"url": "https://github.com/pallets/flask"})

    res = client.get("/pdf/contribution?owner=pallets&repo=flask&issue_number=123")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"


def test_body_size_limit_oversized_payload():
    """Test B: Verify that HTTP POST requests exceeding MAX_PAYLOAD_SIZE_BYTES return 413 Payload Too Large."""
    # Create oversized JSON payload > 1 MB
    oversized_data = {"url": "https://github.com/pallets/flask", "extra": "x" * 1500000}
    response = client.post("/repo/analyze", json=oversized_data)
    assert response.status_code == 413
    assert "Payload too large" in response.json()["detail"]


def test_body_size_limit_streaming_body_without_content_length():
    """Test C: Verify chunked/streaming bodies without Content-Length remain readable and enforce limits."""
    received = []

    async def mock_app(scope, receive, send):
        while True:
            msg = await receive()
            if msg["type"] == "http.request":
                received.append(msg.get("body", b""))
                if not msg.get("more_body", False):
                    break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})

    middleware = BodySizeLimitMiddleware(mock_app, max_bytes=100)

    # 1. Test streaming valid body without Content-Length
    chunks = [b"hello ", b"world"]
    chunk_idx = 0

    async def streaming_receive():
        nonlocal chunk_idx
        if chunk_idx < len(chunks):
            data = chunks[chunk_idx]
            chunk_idx += 1
            return {"type": "http.request", "body": data, "more_body": chunk_idx < len(chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    sent_messages = []

    async def mock_send(msg):
        sent_messages.append(msg)

    scope = {"type": "http", "method": "POST", "path": "/test", "headers": []}
    asyncio.run(middleware(scope, streaming_receive, mock_send))

    assert b"".join(received) == b"hello world"
    assert sent_messages[0]["status"] == 200

    # 2. Test streaming oversized body without Content-Length
    big_chunks = [b"x" * 60, b"y" * 60]
    big_idx = 0

    async def big_receive():
        nonlocal big_idx
        if big_idx < len(big_chunks):
            data = big_chunks[big_idx]
            big_idx += 1
            return {"type": "http.request", "body": data, "more_body": big_idx < len(big_chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}

    big_sent = []

    async def big_send(msg):
        big_sent.append(msg)

    scope_big = {"type": "http", "method": "POST", "path": "/test", "headers": []}
    asyncio.run(middleware(scope_big, big_receive, big_send))

    assert big_sent[0]["status"] == 413


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
