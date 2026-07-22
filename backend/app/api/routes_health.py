import datetime
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def _get_utc_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/health", status_code=status.HTTP_200_OK)
@router.get("/health/live", status_code=status.HTTP_200_OK)
def health_live() -> Dict[str, Any]:
    """Liveness probe: Return status 200 if process is running."""
    return {
        "status": "live",
        "timestamp": _get_utc_timestamp(),
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
def health_ready(
    cache_mgr: CacheManager = Depends(get_cache_manager),
) -> Dict[str, Any]:
    """Readiness probe: Verify lightweight non-blocking backend dependencies."""
    checks = {}

    # 1. Verify Cache Backend Readiness
    try:
        # Check active cache backend handle
        stats = cache_mgr.get_stats()
        checks["cache"] = "ok" if isinstance(stats, dict) else "error"
    except Exception as exc:
        logger.warning("Readiness probe cache check failed: %s", exc)
        checks["cache"] = "error"

    # 2. Verify Config Settings Readiness
    try:
        _ = settings.MODEL_NAME
        checks["config"] = "ok"
    except Exception as exc:
        logger.warning("Readiness probe config check failed: %s", exc)
        checks["config"] = "error"

    all_ready = all(val == "ok" for val in checks.values())
    overall_status = "ready" if all_ready else "degraded"

    return {
        "status": overall_status,
        "timestamp": _get_utc_timestamp(),
        "checks": checks,
    }
