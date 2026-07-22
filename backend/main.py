import inspect
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes_repo import router as repo_router
from app.api.routes_pdf import router as pdf_router
from app.core.config import settings
from app.middleware.body_size_limit import BodySizeLimitMiddleware
from app.services.repository_map_service import RepositoryMapService

logger = logging.getLogger(__name__)

app = FastAPI(title="Repo Guide AI", version="1.0.0")

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

# 4. Request Body Size Limiter
app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.MAX_PAYLOAD_SIZE_BYTES,
)

# 5. Rate Limiting Middleware (IP-based, sliding-window rate limiting)
from app.middleware.rate_limit_middleware import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# 6. Trusted Proxy Headers Middleware (X-Forwarded-For, X-Forwarded-Proto)
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts="*",
)

app.include_router(repo_router)
app.include_router(pdf_router)

@app.on_event("startup")
async def startup_event():
    """Validate the RepositoryMapService constructor at startup."""
    sig = inspect.signature(RepositoryMapService.__init__)
    logger.info("RepositoryMapService constructor signature: %s", sig)

@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "healthy"}
