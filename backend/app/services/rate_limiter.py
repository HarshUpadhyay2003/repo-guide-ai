import logging
import threading
import time
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe sliding-window in-memory rate limiter."""

    def __init__(self, window_seconds: float = 60.0):
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # Dict mapping key -> list of request timestamps within the window
        self._requests: Dict[str, List[float]] = {}
        # Track last pruning time to perform cleanup periodically
        self._last_prune_time = time.time()

    def check_rate_limit(
        self, client_ip: str, category: str, limit_per_minute: int
    ) -> Tuple[bool, int]:
        """Check if request from client_ip for category is permitted.
        
        Args:
            client_ip: Remote IP address of the client.
            category: Route category (analyze, pdf, health, general).
            limit_per_minute: Maximum allowed requests in a rolling 60s window.
            
        Returns:
            Tuple[bool, int]: (allowed, retry_after_seconds)
        """
        now = time.time()
        key = f"{client_ip}:{category}"

        with self._lock:
            # 1. Periodic cleanup of completely stale keys every 30 seconds
            if now - self._last_prune_time > 30.0:
                self._prune_stale_keys_under_lock(now)

            # 2. Prune timestamps for the current key
            timestamps = self._requests.get(key, [])
            cutoff = now - self.window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= limit_per_minute:
                # Limit exceeded: calculate retry-after based on oldest timestamp in window
                oldest = valid_timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                self._requests[key] = valid_timestamps
                return False, retry_after

            # Allowed: record current timestamp
            valid_timestamps.append(now)
            self._requests[key] = valid_timestamps
            return True, 0

    def _prune_stale_keys_under_lock(self, now: float) -> None:
        """Remove keys with no valid timestamps remaining."""
        cutoff = now - self.window_seconds
        stale_keys = []
        for key, timestamps in list(self._requests.items()):
            valid = [t for t in timestamps if t > cutoff]
            if valid:
                self._requests[key] = valid
            else:
                stale_keys.append(key)
        
        for k in stale_keys:
            del self._requests[k]
        self._last_prune_time = now

    def reset(self) -> None:
        """Clear all stored rate limit history."""
        with self._lock:
            self._requests.clear()
            self._last_prune_time = time.time()


# Process-wide RateLimiter singleton instance
rate_limiter = RateLimiter()
