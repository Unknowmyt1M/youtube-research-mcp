import asyncio
import time
from typing import Any, Dict, Optional, Tuple
from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.config import settings


class MemoryCache(BaseCache):
    """Thread-safe and async-safe in-memory cache backend with TTL and negative caching."""

    NEGATIVE_FLAG = "__negative__"

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[Any, bool, float]] = {}  # key -> (value, is_negative, expires_at)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        val, is_neg = await self.get_with_status(key)
        if is_neg:
            return None
        return val

    async def get_with_status(self, key: str) -> Tuple[Optional[Any], bool]:
        v_key = self.format_key(key)
        now = time.time()
        async with self._lock:
            if v_key not in self._store:
                return None, False
            val, is_neg, expires_at = self._store[v_key]
            if expires_at <= now:
                del self._store[v_key]
                return None, False
            return val, is_neg

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        v_key = self.format_key(key)
        now = time.time()
        effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_METADATA)
        expires_at = now + effective_ttl

        async with self._lock:
            # Enforce max memory entries
            if len(self._store) >= self.max_entries and v_key not in self._store:
                # Evict expired first, or oldest
                expired_keys = [k for k, (_, _, exp) in self._store.items() if exp <= now]
                if expired_keys:
                    for k in expired_keys:
                        del self._store[k]
                if len(self._store) >= self.max_entries:
                    # Evict earliest expiring key
                    oldest = min(self._store.items(), key=lambda item: item[1][2])[0]
                    del self._store[oldest]

            self._store[v_key] = (value, False, expires_at)

    async def set_negative(
        self,
        key: str,
        reason: str,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        v_key = self.format_key(key)
        now = time.time()
        effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else settings.NEGATIVE_CACHE_TTL)
        expires_at = now + effective_ttl

        payload = {self.NEGATIVE_FLAG: True, "reason": reason}
        async with self._lock:
            self._store[v_key] = (payload, True, expires_at)

    async def delete(self, key: str) -> bool:
        v_key = self.format_key(key)
        async with self._lock:
            if v_key in self._store:
                del self._store[v_key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def purge_expired(self) -> int:
        now = time.time()
        purged = 0
        async with self._lock:
            keys_to_del = [k for k, (_, _, exp) in self._store.items() if exp <= now]
            for k in keys_to_del:
                del self._store[k]
                purged += 1
        return purged

    async def close(self) -> None:
        await self.clear()
