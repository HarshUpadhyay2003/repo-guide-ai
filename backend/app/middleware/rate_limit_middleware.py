import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing route-category rate limits per client IP."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Determine endpoint category and limit threshold
        if path.startswith("/repo/analyze"):
            category = "analyze"
            limit = settings.RATE_LIMIT_ANALYZE_PER_MINUTE
        elif path.startswith("/pdf/"):
            category = "pdf"
            limit = settings.RATE_LIMIT_PDF_PER_MINUTE
        elif path == "/health" or path.startswith("/health/"):
            category = "health"
            limit = settings.RATE_LIMIT_HEALTH_PER_MINUTE
        else:
            category = "general"
            limit = settings.RATE_LIMIT_GENERAL_PER_MINUTE

        # Resolve client IP (populated accurately by ProxyHeadersMiddleware)
        client_ip = request.client.host if request.client else "127.0.0.1"

        allowed, retry_after = rate_limiter.check_rate_limit(client_ip, category, limit)

        if not allowed:
            logger.warning(
                "[RATE_LIMITED] Client IP: %s | Path: %s | Category: %s | Retry-After: %ds",
                client_ip,
                path,
                category,
                retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded for category '{category}'. Try again in {retry_after} seconds.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
