import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")


class AccessLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware logging structured telemetry for every completed HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        request_id = getattr(request.state, "request_id", "N/A")
        client_ip = request.client.host if request.client else "127.0.0.1"

        logger.info(
            "[HTTP_ACCESS] RequestID: %s | ClientIP: %s | Method: %s | Path: %s | Status: %d | Duration: %.2fms",
            request_id,
            client_ip,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
