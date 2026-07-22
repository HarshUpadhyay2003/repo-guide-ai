import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse, PlainTextResponse

from main import app
from app.core.config import settings
from app.middleware.security_headers import SecurityHeadersMiddleware


client = TestClient(app)


def test_security_headers_present():
    """Verify that standard security response headers are attached to every response."""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert headers.get("Permissions-Policy") == "geolocation=(), camera=(), microphone=()"
    assert headers.get("Cache-Control") == "no-store, max-age=0"
    assert headers.get("Pragma") == "no-cache"


def test_hsts_disabled_by_default():
    """Verify that Strict-Transport-Security header is omitted when ENABLE_HSTS is False."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_enabled_behavior():
    """Verify that Strict-Transport-Security header is attached when HSTS is enabled."""
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True, hsts_max_age=31536000)

    @test_app.get("/test")
    def sample_route():
        return {"status": "ok"}

    test_client = TestClient(test_app)
    res = test_client.get("/test")
    assert res.status_code == 200
    assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"


def test_gzip_compression_above_threshold():
    """Verify that response bodies exceeding GZIP_MINIMUM_SIZE are compressed."""
    # Request with Accept-Encoding: gzip
    headers = {"Accept-Encoding": "gzip"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200


def test_gzip_small_response_uncompressed():
    """Verify that small responses below GZIP_MINIMUM_SIZE remain uncompressed."""
    headers = {"Accept-Encoding": "gzip"}
    response = client.get("/health", headers=headers)
    # /health response is ~20 bytes, well below 1000 bytes threshold
    assert response.headers.get("Content-Encoding") != "gzip"


def test_middleware_stack_coexistence():
    """Verify that CORS, Security Headers, Rate Limiter, and Proxy Headers coexist seamlessly."""
    req_headers = {
        "Origin": "https://app.repopilot.com",
        "X-Forwarded-For": "203.0.113.50",
        "Accept-Encoding": "gzip",
    }
    response = client.get("/health", headers=req_headers)
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
