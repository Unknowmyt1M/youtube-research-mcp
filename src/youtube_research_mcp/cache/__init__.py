from typing import Optional
from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.cache.sqlite import SQLiteCache
from youtube_research_mcp.cache.redis import RedisCache
from youtube_research_mcp.cache.memory import MemoryCache
from youtube_research_mcp.config import settings

_global_cache: Optional[BaseCache] = None


def get_cache() -> BaseCache:
    """Return the configured global cache instance (singleton)."""
    global _global_cache
    if _global_cache is None:
        if settings.CACHE_BACKEND == "redis":
            _global_cache = RedisCache(settings.REDIS_URL)
        elif settings.CACHE_BACKEND == "memory":
            _global_cache = MemoryCache()
        else:
            _global_cache = SQLiteCache(settings.CACHE_DB_PATH)
    return _global_cache


def reset_cache() -> None:
    """Reset the global cache singleton instance (used for testing and runtime switching)."""
    global _global_cache
    _global_cache = None


__all__ = ["BaseCache", "SQLiteCache", "RedisCache", "MemoryCache", "get_cache", "reset_cache"]
