import logging
import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.rate_limiter import rate_limiter
from app.services.pdf_guard import pdf_concurrency_guard


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    rate_limiter.reset()
    pdf_concurrency_guard.reset()
    yield
    rate_limiter.reset()
    pdf_concurrency_guard.reset()


def test_request_id_middleware_generates_header():
    """Verify that X-Request-ID header is generated and attached to response."""
    res = client.get("/health/live")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"].startswith("req_")


def test_request_id_preserves_custom_header():
    """Verify that incoming client/gateway X-Request-ID headers are preserved."""
    headers = {"X-Request-ID": "gateway-tx-9999"}
    res = client.get("/health/live", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == "gateway-tx-9999"


def test_unified_error_format_http_exception():
    """Verify standard error JSON schema for HTTP 404 NOT FOUND errors."""
    res = client.get("/invalid-route-does-not-exist")
    assert res.status_code == 404
    body = res.json()

    assert "error" in body
    err = body["error"]
    assert err["code"] == "HTTP_404_NOT_FOUND"
    assert "message" in err
    assert "request_id" in err
    assert err["request_id"].startswith("req_")
    assert "timestamp" in err
    assert body["detail"] == err["message"]


def test_unified_error_format_validation_error():
    """Verify standard error JSON schema for Pydantic validation errors (HTTP 422)."""
    payload = {"url": "https://not-github.com/owner/repo"}
    res = client.post("/repo/analyze", json=payload)
    assert res.status_code == 422
    body = res.json()

    assert "error" in body
    err = body["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "request_id" in err
    assert "timestamp" in err
    assert "detail" in body


def test_health_liveness_probe():
    """Verify GET /health/live liveness probe response."""
    res = client.get("/health/live")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "live"
    assert "timestamp" in body


def test_health_readiness_probe():
    """Verify GET /health/ready readiness probe response."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "ready"
    assert "timestamp" in body
    assert body.get("checks", {}).get("cache") == "ok"
    assert body.get("checks", {}).get("config") == "ok"


def test_structured_access_logging(caplog):
    """Verify structured HTTP access logging emits RequestID, ClientIP, Method, Path, and Status."""
    with caplog.at_level(logging.INFO):
        res = client.get("/health/live")
        assert res.status_code == 200

    log_records = [rec.message for rec in caplog.records if "[HTTP_ACCESS]" in rec.message]
    assert len(log_records) > 0
    record = log_records[0]
    assert "RequestID:" in record
    assert "ClientIP:" in record
    assert "Method: GET" in record
    assert "Path: /health/live" in record
    assert "Status: 200" in record
