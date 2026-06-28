import time
import threading
from typing import Dict, Optional, Tuple

from app.core.cache.base import CacheBackend

class MemoryCacheBackend(CacheBackend):
    """Thread-safe, in-memory cache backend implementation using a Python dictionary."""

    def __init__(self) -> None:
        # Cache storage holds dictionary mapping: key -> (value_string, expire_at_timestamp)
        self._cache: Dict[str, Tuple[str, Optional[float]]] = {}
        self._lock = threading.Lock()
        self._expired_count = 0

    @property
    def name(self) -> str:
        """The identifier name of the cache backend."""
        return "memory"

    def _is_expired(self, expire_at: Optional[float]) -> bool:
        """Check if the given expiration timestamp has passed."""
        if expire_at is None:
            return False
        return time.time() > expire_at

    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from the in-memory cache.
        
        If the key exists but has expired, it is removed and None is returned.
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expire_at = self._cache[key]
            if self._is_expired(expire_at):
                del self._cache[key]
                self._expired_count += 1
                return None
            return value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Store a string value with an optional TTL (in seconds) in the cache."""
        expire_at = time.time() + ttl if ttl is not None else None
        with self._lock:
            self._cache[key] = (value, expire_at)

    def delete(self, key: str) -> bool:
        """Remove a key from the in-memory cache.
        
        Returns True if the key existed and was not expired prior to deletion, False otherwise.
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            _, expire_at = self._cache[key]
            del self._cache[key]
            # If it was already expired, count it as expired and return False
            if self._is_expired(expire_at):
                self._expired_count += 1
                return False
            return True

    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache and has not expired."""
        with self._lock:
            if key not in self._cache:
                return False
            
            _, expire_at = self._cache[key]
            if self._is_expired(expire_at):
                del self._cache[key]
                self._expired_count += 1
                return False
            return True

    def clear(self) -> None:
        """Clear all entries from the in-memory cache."""
        with self._lock:
            self._cache.clear()

    def invalidate(self, key: str) -> bool:
        """Semantically invalidate (delete) a key from the cache.
        
        Returns True if the key existed and was deleted, False otherwise.
        """
        return self.delete(key)

    def get_current_entries(self) -> int:
        """Get the count of active, non-expired entries in the cache."""
        with self._lock:
            now = time.time()
            # Clean up expired entries under lock to keep stats consistent
            expired_keys = [k for k, (_, expire_at) in self._cache.items() if expire_at is not None and now > expire_at]
            for k in expired_keys:
                del self._cache[k]
                self._expired_count += 1
            return len(self._cache)

    def get_expired_entries(self) -> int:
        """Get the cumulative count of passively expired entries."""
        with self._lock:
            return self._expired_count
