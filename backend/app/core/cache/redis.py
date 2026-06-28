from typing import Optional

from app.core.cache.base import CacheBackend

class RedisCacheBackend(CacheBackend):
    """Placeholder Redis Cache Backend.
    
    This class defines the structure and satisfies the interface for future Redis caching integration.
    Currently, all methods raise NotImplementedError.
    """

    @property
    def name(self) -> str:
        """The identifier name of the cache backend."""
        return "redis"

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def delete(self, key: str) -> bool:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def exists(self, key: str) -> bool:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def clear(self) -> None:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def invalidate(self, key: str) -> bool:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def get_current_entries(self) -> int:
        raise NotImplementedError("Redis cache backend is not implemented yet.")

    def get_expired_entries(self) -> int:
        raise NotImplementedError("Redis cache backend is not implemented yet.")
