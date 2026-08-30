import asyncio
import json
import logging
import time
from typing import Any, Optional, Tuple
import urllib.parse

from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.config import settings

logger = logging.getLogger(__name__)


def mask_redis_url(url: str) -> str:
    """Mask password or credentials in Redis connection URL for safe logging."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.password:
            user = parsed.username or ""
            host = parsed.hostname or "localhost"
            port = f":{parsed.port}" if parsed.port else ""
            netloc = f"{user}:***@{host}{port}"
            return urllib.parse.urlunparse(
                (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
            )
        return url
    except Exception:
        return "redis://***"


class RedisCache(BaseCache):
    """Production-grade Redis distributed cache backend with pooling, timeouts, and graceful degradation."""

    NEGATIVE_FLAG = "__negative__"

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client = None
        self._lock = asyncio.Lock()

    async def _get_client(self):
        """Lazily initialize Redis client with connection pooling, timeout bounds, and concurrency protection."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        import redis.asyncio as aioredis

                        self._client = aioredis.from_url(
                            self.redis_url,
                            protocol=2,
                            max_connections=settings.REDIS_MAX_CONNECTIONS,
                            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
                            encoding="utf-8",
                            decode_responses=True,
                        )
                    except ImportError:
                        raise RuntimeError(
                            "Redis package is not installed. Install with `pip install youtube-research-mcp[redis]`."
                        )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache. Returns None if missing, expired, negative, or Redis unavailable."""
        val, is_neg = await self.get_with_status(key)
        if is_neg:
            return None
        return val

    async def get_with_status(self, key: str) -> Tuple[Optional[Any], bool]:
        """Retrieve value and negative-cache boolean flag (value, is_negative).

        Degrades gracefully to (None, False) on Redis connection or parsing errors.
        """
        formatted = self.format_key(key)
        try:
            client = await self._get_client()
            raw = await client.get(formatted)
            if not raw:
                return None, False

            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as jde:
                logger.warning(
                    f"Redis cache entry for key '{formatted}' contains malformed JSON ({jde}). Treating as cache miss."
                )
                return None, False

            if not isinstance(payload, dict):
                return None, False

            is_neg = bool(payload.get("is_negative", False))
            return payload.get("value"), is_neg

        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.warning(
                f"Redis cache operation failed on get('{formatted}') [{mask_redis_url(self.redis_url)}]: {type(e).__name__} ({str(e)}). Continuing without cache."
            )
            return None, False

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store positive result with TTL expiration. Degrades gracefully on failure."""
        eff_ttl = (
            ttl
            if ttl is not None
            else (ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_METADATA)
        )
        formatted = self.format_key(key)
        payload = {
            "value": value,
            "is_negative": False,
            "created_at": time.time(),
        }
        try:
            raw = json.dumps(payload)
            client = await self._get_client()
            await client.set(formatted, raw, ex=eff_ttl)
        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.warning(
                f"Redis cache operation failed on set('{formatted}') [{mask_redis_url(self.redis_url)}]: {type(e).__name__} ({str(e)})."
            )

    async def set_negative(
        self,
        key: str,
        reason: str,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store short-lived negative result (e.g. video has no captions). Degrades gracefully on failure."""
        eff_ttl = (
            ttl
            if ttl is not None
            else (ttl_seconds if ttl_seconds is not None else settings.NEGATIVE_CACHE_TTL)
        )
        formatted = self.format_key(key)
        payload = {
            "value": {self.NEGATIVE_FLAG: True, "reason": reason},
            "is_negative": True,
            "created_at": time.time(),
        }
        try:
            raw = json.dumps(payload)
            client = await self._get_client()
            await client.set(formatted, raw, ex=eff_ttl)
        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.warning(
                f"Redis cache operation failed on set_negative('{formatted}') [{mask_redis_url(self.redis_url)}]: {type(e).__name__} ({str(e)})."
            )

    async def delete(self, key: str) -> bool:
        """Remove key from Redis cache."""
        formatted = self.format_key(key)
        try:
            client = await self._get_client()
            res = await client.delete(formatted)
            return res > 0
        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.warning(
                f"Redis cache operation failed on delete('{formatted}') [{mask_redis_url(self.redis_url)}]: {type(e).__name__} ({str(e)})."
            )
            return False

    async def clear(self) -> None:
        """Clear all cache entries under the active version prefix."""
        try:
            client = await self._get_client()
            version = settings.CACHE_SCHEMA_VERSION
            cursor = 0
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor, match=f"{version}:*", count=100
                )
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.warning(
                f"Redis cache operation failed on clear() [{mask_redis_url(self.redis_url)}]: {type(e).__name__} ({str(e)})."
            )

    async def purge_expired(self) -> int:
        """Redis automatically evicts expired keys via native TTLs."""
        return 0

    async def close(self) -> None:
        """Gracefully close client connection pool."""
        if self._client is not None:
            try:
                if hasattr(self._client, "aclose"):
                    res = self._client.aclose()
                    if asyncio.iscoroutine(res):
                        await res
                elif hasattr(self._client, "close"):
                    res = self._client.close()
                    if asyncio.iscoroutine(res):
                        await res
            except Exception:
                pass
            finally:
                self._client = None
