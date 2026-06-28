from abc import ABC, abstractmethod
from typing import Optional

# RATIONALE FOR BACKEND ABSTRACTION:
# Decoupling cache operations from storage implementations allows the application
# to swap backends (e.g. from local memory to Redis or cloud caching) with zero service refactoring.
# It also facilitates testing, mocking, and multi-tier caching architectures.
class CacheBackend(ABC):
    """Abstract base class representing a generic cache backend."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the cache backend (e.g., 'memory', 'redis')."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from the cache.
        
        Returns None if the key does not exist or has expired.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Store a value in the cache with an optional time-to-live (TTL) in seconds."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from the cache.
        
        Returns True if the key existed and was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache and has not expired."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all keys from the cache."""
        pass

    @abstractmethod
    def invalidate(self, key: str) -> bool:
        """Semantically invalidate (delete) a key from the cache.
        
        Returns True if the key existed and was deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_current_entries(self) -> int:
        """Get the count of active, non-expired entries in the cache."""
        pass

    @abstractmethod
    def get_expired_entries(self) -> int:
        """Get the cumulative count of passively expired entries."""
        pass
