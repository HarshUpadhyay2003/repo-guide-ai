from functools import lru_cache

from app.core.config import settings
from app.core.cache.base import CacheBackend
from app.core.cache.memory import MemoryCacheBackend
from app.core.cache.redis import RedisCacheBackend
from app.core.cache.manager import CacheManager

@lru_cache(maxsize=1)
def get_cache_backend() -> CacheBackend:
    """Return a singleton instance of the configured CacheBackend."""
    backend_type = settings.CACHE_BACKEND.lower().strip()
    if backend_type == "redis":
        return RedisCacheBackend()
    
    # Default fallback to memory cache backend
    return MemoryCacheBackend()

@lru_cache(maxsize=1)
def get_cache_manager() -> CacheManager:
    """Return a singleton instance of the CacheManager."""
    backend = get_cache_backend()
    return CacheManager(backend)
