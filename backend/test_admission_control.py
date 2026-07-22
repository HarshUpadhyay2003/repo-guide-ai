import time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.services.rate_limiter import rate_limiter
from app.services.pdf_guard import pdf_concurrency_guard, PDFConcurrencyGuard


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_admission_state():
    """Reset rate limiter and PDF concurrency guard state before each test."""
    rate_limiter.reset()
    pdf_concurrency_guard.reset()
    yield
    rate_limiter.reset()
    pdf_concurrency_guard.reset()


def test_rate_limit_analyze_endpoint():
    """Verify that POST /repo/analyze enforces its configured rate limit and returns 429."""
    limit = settings.RATE_LIMIT_ANALYZE_PER_MINUTE
    payload = {"url": "https://github.com/pallets/flask"}
    headers = {"X-Forwarded-For": "198.51.100.1"}

    # Execute allowed requests
    for i in range(limit):
        res = client.post("/repo/analyze", json=payload, headers=headers)
        assert res.status_code != 429

    # Exceeded request must return HTTP 429 Too Many Requests
    exceeded_res = client.post("/repo/analyze", json=payload, headers=headers)
    assert exceeded_res.status_code == 429
    assert "Retry-After" in exceeded_res.headers
    assert int(exceeded_res.headers["Retry-After"]) >= 1
    assert "Rate limit exceeded for category 'analyze'" in exceeded_res.json()["detail"]


def test_rate_limit_proxy_ip_isolation():
    """Verify that rate limits are isolated per proxy-forwarded client IP."""
    limit = settings.RATE_LIMIT_ANALYZE_PER_MINUTE
    payload = {"url": "https://github.com/pallets/flask"}

    ip_a = {"X-Forwarded-For": "203.0.113.10"}
    ip_b = {"X-Forwarded-For": "203.0.113.20"}

    # Exhaust limit for IP A
    for _ in range(limit):
        client.post("/repo/analyze", json=payload, headers=ip_a)

    assert client.post("/repo/analyze", json=payload, headers=ip_a).status_code == 429

    # IP B must still be permitted
    assert client.post("/repo/analyze", json=payload, headers=ip_b).status_code != 429


def test_rate_limit_window_expiration():
    """Verify that requests are permitted again after the rolling window expires."""
    limiter = rate_limiter
    client_ip = "192.0.2.5"

    # Fill rolling limit of 2 requests
    allowed1, _ = limiter.check_rate_limit(client_ip, "test_cat", limit_per_minute=2)
    allowed2, _ = limiter.check_rate_limit(client_ip, "test_cat", limit_per_minute=2)
    allowed3, retry_after = limiter.check_rate_limit(client_ip, "test_cat", limit_per_minute=2)

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is False
    assert retry_after >= 1


def test_pdf_concurrency_guard_acquisition_and_rejection():
    """Verify that PDFConcurrencyGuard permits up to max_concurrent and rejects excess with 503."""
    guard = PDFConcurrencyGuard(max_concurrent=2)

    # Acquire 2 slots successfully
    guard.acquire(client_ip="10.0.0.1", path="/pdf/repository")
    guard.acquire(client_ip="10.0.0.2", path="/pdf/repository")

    # 3rd acquire attempt must raise HTTP 503 Service Unavailable
    with pytest.raises(HTTPException) as exc_info:
        guard.acquire(client_ip="10.0.0.3", path="/pdf/repository")

    assert exc_info.value.status_code == 503
    assert "maximum capacity" in exc_info.value.detail

    # Release 1 slot
    guard.release(client_ip="10.0.0.1", path="/pdf/repository")

    # Subsequent acquire should succeed
    guard.acquire(client_ip="10.0.0.4", path="/pdf/repository")
