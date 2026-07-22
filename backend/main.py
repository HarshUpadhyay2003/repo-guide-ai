from contextlib import asynccontextmanager
import inspect
import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes_repo import router as repo_router
from app.api.routes_pdf import router as pdf_router
from app.api.routes_health import router as health_router
from app.core.config import settings
from app.core.errors import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.middleware.body_size_limit import BodySizeLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.access_logger import AccessLoggerMiddleware
from app.services.repository_map_service import RepositoryMapService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """FastAPI lifespan context manager replacing deprecated startup/shutdown event handlers."""
    sig = inspect.signature(RepositoryMapService.__init__)
    logger.info("Application starting up. RepositoryMapService constructor signature: %s", sig)
    yield
    logger.info("Application shutting down cleanly.")


app = FastAPI(title="Repo Guide AI", version="1.0.0", lifespan=lifespan)

# Register Centralized Exception Handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 1. GZip Compression Middleware (innermost middleware wrapper)
if settings.ENABLE_GZIP:
    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.GZIP_MINIMUM_SIZE,
    )

# 2. Security Headers Middleware (attaches defensive headers to all responses)
from app.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.ENABLE_HSTS,
    hsts_max_age=settings.HSTS_MAX_AGE,
)

# 3. CORS Configuration (Environment-driven, compliant credential handling)
origins = settings.ALLOWED_ORIGINS
allow_creds = "*" not in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Rate Limiting Middleware (IP-based, sliding-window rate limiting)
from app.middleware.rate_limit_middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# 5. Request Body Size Limiter
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.MAX_PAYLOAD_SIZE_BYTES,
)

# 6. Structured HTTP Access Logger
app.add_middleware(AccessLoggerMiddleware)

# 7. Request ID Correlation Middleware
app.add_middleware(RequestIDMiddleware)

# 8. Trusted Proxy Headers Middleware (X-Forwarded-For, X-Forwarded-Proto - outermost wrapper)
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts="*",
)

app.include_router(repo_router)
app.include_router(pdf_router)
app.include_router(health_router)
