import logging
import threading
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Thread-local storage for tracking current analysis generation
_thread_local = threading.local()


class InvalidationTracker:
    """Thread-safe registry for repository invalidation generations.
    
    Tracks monotonic generation counters and last-accessed times for repositories
    to prevent stale cache writes. Integrates thread-local context propagation
    for thread-pool execution flows.
    """

    def __init__(self, idle_timeout_seconds: float = 86400.0) -> None:
        """Initialize the invalidation tracker.
        
        Args:
            idle_timeout_seconds: Time in seconds of inactivity before an entry is pruned.
                                  Defaults to 86400 (24 hours).
        """
        # Dictionary mapping: repo_key -> (generation, last_accessed_timestamp)
        self._entries: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()
        self.idle_timeout_seconds = idle_timeout_seconds

    def _normalize_key(self, repo_key: str) -> str:
        """Normalize a repository key to a canonical format."""
        if not isinstance(repo_key, str) or not repo_key.strip():
            raise ValueError("Repository key must be a non-empty string.")
        return repo_key.strip().lower()

    def get_generation(self, repo_key: str) -> int:
        """Get the current generation of a repository.
        
        Updates the repository's last-accessed timestamp.
        """
        key = self._normalize_key(repo_key)
        now = time.time()
        with self._lock:
            if key not in self._entries:
                return 0
            
            gen, _ = self._entries[key]
            self._entries[key] = (gen, now)
            return gen

    def increment_generation(self, repo_key: str) -> int:
        """Increment and return the generation of a repository.
        
        Updates the repository's last-accessed timestamp and triggers
        the inactivity pruning sweep.
        """
        key = self._normalize_key(repo_key)
        now = time.time()
        with self._lock:
            # First, perform pruning sweep for inactive entries
            self._prune_inactive_entries_under_lock(now)
            
            current_gen = 0
            if key in self._entries:
                current_gen, _ = self._entries[key]
                
            next_gen = current_gen + 1
            self._entries[key] = (next_gen, now)
            logger.info("Incremented generation for repository '%s': %d -> %d", key, current_gen, next_gen)
            return next_gen

    def _prune_inactive_entries_under_lock(self, current_time: float) -> None:
        """Scan and remove entries that have exceeded the inactivity timeout."""
        expired_keys = [
            k for k, (_, last_accessed) in self._entries.items()
            if current_time - last_accessed > self.idle_timeout_seconds
        ]
        for k in expired_keys:
            del self._entries[k]
            logger.info("Pruned inactive repository tracker entry: '%s' (exceeded %s seconds inactivity)", k, self.idle_timeout_seconds)

    # --- Thread-local contexts ---

    def set_thread_generation(self, generation: int) -> None:
        """Set the generation context for the current thread."""
        if not isinstance(generation, int):
            raise TypeError("Generation must be an integer.")
        _thread_local.generation = generation

    def get_thread_generation(self) -> Optional[int]:
        """Get the generation context for the current thread."""
        return getattr(_thread_local, "generation", None)

    def clear_thread_generation(self) -> None:
        """Clear the generation context for the current thread."""
        if hasattr(_thread_local, "generation"):
            delattr(_thread_local, "generation")

    def init_worker(self, generation: Optional[int]) -> None:
        """Initialize a worker thread-local generation context.
        
        Suitable for ThreadPoolExecutor initializers.
        """
        if generation is not None:
            self.set_thread_generation(generation)
        else:
            self.clear_thread_generation()


# Global invalidation tracker singleton instance
invalidation_tracker = InvalidationTracker()
