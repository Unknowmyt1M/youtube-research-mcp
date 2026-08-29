import json
import time
from typing import Any, Optional, Tuple
from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.config import settings


class RedisCache(BaseCache):
    """Redis distributed cache backend with full BaseCache interface compatibility."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis

                self._client = aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
            except ImportError:
                raise RuntimeError(
                    "Redis package is not installed. Install with `pip install youtube-research-mcp[redis]`."
                )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache. Returns None if missing, expired, or negative."""
        val, is_neg = await self.get_with_status(key)
        if is_neg:
            return None
        return val

    async def get_with_status(self, key: str) -> Tuple[Optional[Any], bool]:
        """Retrieve value and negative-cache boolean flag. Returns (value, is_negative)."""
        formatted = self.format_key(key)
        try:
            client = await self._get_client()
            raw = await client.get(formatted)
            if not raw:
                return None, False
            payload = json.loads(raw)
            is_neg = bool(payload.get("is_negative", False))
            return payload.get("value"), is_neg
        except Exception:
            return None, False

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store positive result with TTL expiration."""
        eff_ttl = ttl if ttl is not None else ttl_seconds
        if eff_ttl is None:
            eff_ttl = settings.CACHE_TTL_SEARCH

        formatted = self.format_key(key)
        payload = {
            "value": value,
            "is_negative": False,
            "created_at": time.time(),
        }
        try:
            client = await self._get_client()
            await client.set(formatted, json.dumps(payload), ex=eff_ttl)
        except Exception:
            pass

    async def set_negative(
        self,
        key: str,
        reason: str,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store short-lived negative result (e.g. video has no captions)."""
        eff_ttl = ttl if ttl is not None else ttl_seconds
        if eff_ttl is None:
            eff_ttl = settings.NEGATIVE_CACHE_TTL

        formatted = self.format_key(key)
        payload = {
            "value": {"reason": reason},
            "is_negative": True,
            "created_at": time.time(),
        }
        try:
            client = await self._get_client()
            await client.set(formatted, json.dumps(payload), ex=eff_ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> bool:
        """Remove key from Redis cache."""
        formatted = self.format_key(key)
        try:
            client = await self._get_client()
            res = await client.delete(formatted)
            return res > 0
        except Exception:
            return False

    async def clear(self) -> None:
        """Clear all cache entries under the active version prefix."""
        try:
            client = await self._get_client()
            version = settings.CACHE_SCHEMA_VERSION
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=f"{version}:*", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

    async def purge_expired(self) -> int:
        """Redis automatically evicts expired keys via native TTLs."""
        return 0

    async def close(self) -> None:
        """Close client connection pool."""
        if self._client:
            await self._client.close()
            self._client = None
