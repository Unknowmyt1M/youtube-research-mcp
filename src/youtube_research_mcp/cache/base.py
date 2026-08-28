from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCache(ABC):
    """Abstract Base Cache interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache by key. Returns None on miss or expired."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store item in cache with TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove item from cache."""
        pass

    @abstractmethod
    async def clear_expired(self) -> int:
        """Purge all expired entries from cache. Returns count of purged items."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection / release resources."""
        pass
