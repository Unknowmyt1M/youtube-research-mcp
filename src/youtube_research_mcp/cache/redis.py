import json
import time
from typing import Any, Optional
from youtube_research_mcp.cache.base import BaseCache


class RedisCache(BaseCache):
    """Redis distributed cache backend with fallback support."""

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
        try:
            client = await self._get_client()
            val = await client.get(key)
            if val:
                return json.loads(val)
        except Exception:
            return None
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            client = await self._get_client()
            val = json.dumps(value)
            await client.set(key, val, ex=ttl_seconds)
        except Exception:
            pass

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            res = await client.delete(key)
            return res > 0
        except Exception:
            return False

    async def clear_expired(self) -> int:
        # Redis automatically purges keys on TTL expiration
        return 0

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
