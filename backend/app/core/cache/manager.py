import datetime
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Union

from app.core.cache.base import CacheBackend
from app.core.cache.keys import get_repo_summary_key, get_issue_guidance_key

logger = logging.getLogger(__name__)

def _validate_json_compatible(obj: Any) -> None:
    """Recursively validate that the object is JSON-compatible.
    
    Permitted types: dict, list, str, int, float, bool, None.
    Tuples, datetime objects, and other custom objects are explicitly disallowed.
    """
    if obj is None:
        return
    # bool is a subclass of int, so check bool first
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float, str)):
        return
    if isinstance(obj, list):
        for item in obj:
            _validate_json_compatible(item)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"JSON dict keys must be strings, got '{type(k).__name__}'")
            _validate_json_compatible(v)
        return
    raise TypeError(
        f"Unsupported type '{type(obj).__name__}' passed to cache. "
        f"Only plain dict, list, str, int, float, bool, and None are allowed."
    )

class CacheManager:
    """Manager that handles serialization and coordinates operations with a configured CacheBackend.
    
    This class serves as the single entry point for application services interacting with the cache.
    It tracks cache operations stats in a thread-safe manner.
    """

    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend
        self._hits = 0
        self._misses = 0
        self._writes = 0
        self._deletes = 0
        self._lookup_time_ms = 0.0
        self._write_time_ms = 0.0
        self._stats_lock = threading.Lock()

    @property
    def backend_name(self) -> str:
        """Get the active cache backend identifier name (e.g. 'memory')."""
        return self._backend.name

    def get_backend_name(self) -> str:
        """Get the active cache backend identifier name."""
        return self.backend_name

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a deserialized payload from the cache metadata wrapper.
        
        Tracks hits, misses, and lookup duration. Returns None if key is missing or expired.
        """
        start_time = time.perf_counter()
        try:
            val_str = self._backend.get(key)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            with self._stats_lock:
                self._lookup_time_ms += duration_ms

        if val_str is None:
            with self._stats_lock:
                self._misses += 1
            return None

        try:
            wrapper = json.loads(val_str)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to deserialize cache key %s: %s", key, exc)
            with self._stats_lock:
                self._misses += 1
            return None

        # RATIONALE FOR METADATA WRAPPER:
        # Wrapping the payload with created_at and expires_at provides a backend-agnostic
        # debugging and diagnostics layer. Callers only see the unwrapped payload,
        # keeping the metadata storage implementation completely transparent to them.
        if isinstance(wrapper, dict) and "payload" in wrapper:
            with self._stats_lock:
                self._hits += 1
            return wrapper["payload"]

        # Fallback in case raw (unwrapped) value is encountered
        with self._stats_lock:
            self._hits += 1
        return wrapper

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Serialize and store a value wrapped in a metadata dict.
        
        Raises TypeError if the value is not strictly JSON-compatible.
        Tracks write duration.
        """
        _validate_json_compatible(value)

        # Generate ISO8601 timestamps in UTC
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        created_at_str = now_utc.isoformat()
        
        if ttl is not None:
            expires_at_str = (now_utc + datetime.timedelta(seconds=ttl)).isoformat()
        else:
            expires_at_str = None

        wrapper = {
            "payload": value,
            "created_at": created_at_str,
            "expires_at": expires_at_str,
        }

        val_str = json.dumps(wrapper)
        
        start_time = time.perf_counter()
        try:
            self._backend.set(key, val_str, ttl)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            with self._stats_lock:
                self._write_time_ms += duration_ms

        with self._stats_lock:
            self._writes += 1

    def delete(self, key: str) -> bool:
        """Delete a key from the cache. Returns True if deleted, False otherwise."""
        deleted = self._backend.delete(key)
        with self._stats_lock:
            self._deletes += 1
        return deleted

    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired in the cache."""
        return self._backend.exists(key)

    def clear(self) -> None:
        """Clear all keys in the underlying backend."""
        self._backend.clear()

    def invalidate(self, key: str) -> bool:
        """Semantically invalidate (delete) a key from the cache.
        
        Delegates directly to the backend. Returns True if deleted, False otherwise.
        """
        deleted = self._backend.invalidate(key)
        with self._stats_lock:
            self._deletes += 1
        return deleted

    # RATIONALE FOR NAMESPACE INVALIDATION PLACEHOLDERS:
    # Defining specific namespace invalidation methods early allows downstream services
    # to adopt the correct semantic eviction patterns from the start, avoiding interface
    # breaking changes when the full multi-tier invalidation logic is implemented in Stage 8.6.
    def invalidate_repository(self, owner: str, repo: str) -> None:
        """Placeholder for invalidating all cache entries associated with a repository.
        
        TODO: Implement full scan/pattern invalidation in Stage 8.6.
        """
        self.invalidate_summary(owner, repo)

    def invalidate_issue(self, owner: str, repo: str, issue_number: Union[int, str]) -> None:
        """Placeholder for invalidating guidance for a specific issue.
        
        TODO: Implement full scan/pattern invalidation in Stage 8.6.
        """
        key = get_issue_guidance_key(owner, repo, issue_number)
        self.invalidate(key)

    def invalidate_summary(self, owner: str, repo: str) -> None:
        """Placeholder for invalidating repository summary.
        
        TODO: Implement full scan/pattern invalidation in Stage 8.6.
        """
        key = get_repo_summary_key(owner, repo)
        self.invalidate(key)

    def cache_or_compute(
        self,
        key: str,
        ttl: Optional[int],
        compute_function: Callable[[], Any],
        serializer: Optional[Callable[[Any], Any]] = None,
    ) -> Any:
        """Retrieve a value from the cache. On miss, call compute_function, serialize, store, and return."""
        # 1. Lookup cache
        cached_val = self.get(key)
        if cached_val is not None:
            return cached_val

        # 2. Execute compute function on miss
        computed_val = compute_function()

        # 3. Apply serializer (if supplied)
        serialized_val = serializer(computed_val) if serializer is not None else computed_val

        # 4. Store serialized payload and return
        self.set(key, serialized_val, ttl)
        return serialized_val

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for cache hits, misses, writes, and deletes."""
        try:
            current_entries = self._backend.get_current_entries()
        except NotImplementedError:
            current_entries = 0

        try:
            expired_entries = self._backend.get_expired_entries()
        except NotImplementedError:
            expired_entries = 0

        with self._stats_lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "writes": self._writes,
                "deletes": self._deletes,
                "lookup_time_ms": round(self._lookup_time_ms, 2),
                "write_time_ms": round(self._write_time_ms, 2),
                "current_entries": current_entries,
                "expired_entries": expired_entries,
                "backend_name": self.backend_name,
            }
