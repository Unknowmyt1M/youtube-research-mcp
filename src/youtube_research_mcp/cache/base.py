from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple
from youtube_research_mcp.config import settings


class BaseCache(ABC):
    """Abstract caching interface with versioning and negative caching."""

    def format_key(self, raw_key: str) -> str:
        """Namespace key with current cache schema version."""
        version = settings.CACHE_SCHEMA_VERSION
        if raw_key.startswith(f"{version}:"):
            return raw_key
        return f"{version}:{raw_key}"

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache. Returns None if missing or expired."""
        pass

    @abstractmethod
    async def get_with_status(self, key: str) -> Tuple[Optional[Any], bool]:
        """Retrieve value and negative-cache boolean flag. (value, is_negative)."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store value in cache with TTL in seconds."""
        pass

    @abstractmethod
    async def set_negative(
        self,
        key: str,
        reason: str,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store short-lived negative result in cache (e.g. video has no transcripts)."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove key from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def purge_expired(self) -> int:
        """Physically purge expired rows."""
        pass

    async def close(self) -> None:
        """Close cache resources."""
        pass
