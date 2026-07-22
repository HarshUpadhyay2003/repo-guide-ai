import logging
import threading
from typing import Optional
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFConcurrencyGuard:
    """Thread-safe non-blocking concurrency guard for synchronous PDF rendering tasks."""

    def __init__(self, max_concurrent: Optional[int] = None):
        self._lock = threading.Lock()
        self._max_concurrent = max_concurrent
        self._active_count = 0

    @property
    def max_concurrent(self) -> int:
        if self._max_concurrent is not None:
            return self._max_concurrent
        return getattr(settings, "MAX_CONCURRENT_PDF_GENERATIONS", 3)

    def acquire(self, client_ip: str = "127.0.0.1", path: str = "/pdf") -> None:
        """Attempt to acquire a PDF rendering execution slot non-blocking.
        
        If active count meets or exceeds max_concurrent limit, immediately log warning telemetry
        and raise HTTP 503 Service Unavailable exception.
        """
        with self._lock:
            limit = self.max_concurrent
            if self._active_count >= limit:
                logger.warning(
                    "[PDF_CONCURRENCY_REJECTED] Client IP: %s | Path: %s | Active: %d | Limit: %d | Reason: Capacity exhausted",
                    client_ip,
                    path,
                    self._active_count,
                    limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="PDF generation service is currently at maximum capacity. Please retry shortly.",
                )

            self._active_count += 1
            current = self._active_count
            logger.info(
                "[PDF_CONCURRENCY_ACQUIRED] Client IP: %s | Path: %s | Active: %d/%d",
                client_ip,
                path,
                current,
                limit,
            )

    def release(self, client_ip: str = "127.0.0.1", path: str = "/pdf") -> None:
        """Release a PDF rendering execution slot."""
        with self._lock:
            if self._active_count > 0:
                self._active_count -= 1
            current = self._active_count
            limit = self.max_concurrent
            logger.info(
                "[PDF_CONCURRENCY_RELEASED] Client IP: %s | Path: %s | Active: %d/%d",
                client_ip,
                path,
                current,
                limit,
            )

    def reset(self) -> None:
        """Reset active count (useful for test isolation)."""
        with self._lock:
            self._active_count = 0


# Process-wide PDF concurrency guard singleton
pdf_concurrency_guard = PDFConcurrencyGuard()
