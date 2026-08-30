import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from youtube_research_mcp.cache import get_cache, reset_cache
from youtube_research_mcp.cache.redis import RedisCache, mask_redis_url
from youtube_research_mcp.config import settings


class AsyncMockRedisClient:
    """Mock Redis client simulating aioredis asynchronous commands."""

    def __init__(self):
        self.store: Dict[str, Tuple[str, Optional[float]]] = {}  # key -> (raw_json, expire_at)
        self.closed = False

    async def get(self, key: str) -> Optional[str]:
        if key not in self.store:
            return None
        val, exp = self.store[key]
        if exp is not None and time.time() > exp:
            del self.store[key]
            return None
        return val

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        exp = time.time() + ex if ex is not None else None
        self.store[key] = (value, exp)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                deleted += 1
        return deleted

    async def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        _, exp = self.store[key]
        if exp is None:
            return -1
        remaining = int(exp - time.time())
        return max(0, remaining)

    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 100) -> Tuple[int, List[str]]:
        prefix = match.replace("*", "") if match else ""
        matched = [k for k in self.store.keys() if k.startswith(prefix)]
        return 0, matched

    async def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.closed = True


def test_mask_redis_url():
    """Verify passwords in Redis URLs are masked in logs."""
    assert mask_redis_url("redis://localhost:6379/0") == "redis://localhost:6379/0"
    assert (
        mask_redis_url("redis://:supersecret123@redis.cloud.com:6380/1")
        == "redis://:***@redis.cloud.com:6380/1"
    )
    assert (
        mask_redis_url("redis://admin:mypassword@localhost:6379/0")
        == "redis://admin:***@localhost:6379/0"
    )
    assert mask_redis_url("") == ""


def test_cache_factory_selects_redis():
    """Verify that CACHE_BACKEND=redis causes get_cache() to return RedisCache instance."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CACHE_BACKEND", "redis")
        mp.setattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/2")
        reset_cache()
        cache = get_cache()
        assert isinstance(cache, RedisCache)
        assert cache.redis_url == "redis://127.0.0.1:6379/2"
        reset_cache()


@pytest.mark.asyncio
async def test_redis_client_uses_protocol_2_for_redis_5_compatibility():
    """REDIS-001 Regression Test: Verify aioredis client is configured with protocol=2 for universal Redis <6 & >=6 compatibility."""
    cache = RedisCache("redis://localhost:6380/0")
    mock_client = AsyncMockRedisClient()

    with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
        client = await cache._get_client()
        assert client is mock_client
        mock_from_url.assert_called_once()
        _, kwargs = mock_from_url.call_args
        assert kwargs.get("protocol") == 2
        assert kwargs.get("socket_timeout") == settings.REDIS_SOCKET_TIMEOUT
        assert kwargs.get("socket_connect_timeout") == settings.REDIS_CONNECT_TIMEOUT
        assert kwargs.get("max_connections") == settings.REDIS_MAX_CONNECTIONS
    await cache.close()


@pytest.mark.asyncio
async def test_redis_concurrent_client_initialization():
    """Verify concurrent _get_client calls do not create duplicate Redis clients."""
    cache = RedisCache("redis://localhost:6379/0")
    mock_client = AsyncMockRedisClient()

    with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
        tasks = [cache._get_client() for _ in range(25)]
        clients = await asyncio.gather(*tasks)

        assert mock_from_url.call_count == 1
        for c in clients:
            assert c is mock_client
    await cache.close()


@pytest.mark.asyncio
async def test_redis_ttl_parity_defaults():
    """REDIS-003 Test: Verify Redis default positive TTL matches SQLite (7 days), and overrides work."""
    cache = RedisCache("redis://localhost:6379/0")
    mock_redis = AsyncMock()
    cache._client = mock_redis

    # 1. Default positive TTL (should default to CACHE_TTL_METADATA = 604800s / 7d)
    await cache.set("default_key", {"foo": "bar"})
    _, kwargs = mock_redis.set.call_args
    assert kwargs.get("ex") == settings.CACHE_TTL_METADATA
    assert kwargs.get("ex") == 604800

    # 2. Explicit ttl overrides default
    mock_redis.reset_mock()
    await cache.set("override_key", {"foo": "bar"}, ttl=300)
    _, kwargs = mock_redis.set.call_args
    assert kwargs.get("ex") == 300

    # 3. Explicit ttl_seconds overrides default
    mock_redis.reset_mock()
    await cache.set("override_sec_key", {"foo": "bar"}, ttl_seconds=120)
    _, kwargs = mock_redis.set.call_args
    assert kwargs.get("ex") == 120

    # 4. Default negative TTL (should default to NEGATIVE_CACHE_TTL = 600s / 10m)
    mock_redis.reset_mock()
    await cache.set_negative("neg_key", reason="not found")
    _, kwargs = mock_redis.set.call_args
    assert kwargs.get("ex") == settings.NEGATIVE_CACHE_TTL
    assert kwargs.get("ex") == 600


@pytest.mark.asyncio
async def test_redis_positive_and_negative_cache_lifecycle():
    """Verify positive caching, negative caching, TTL, get, and delete on RedisCache."""
    cache = RedisCache("redis://localhost:6379/0")
    cache._client = AsyncMockRedisClient()

    # 1. Positive cache
    await cache.set("test_key", {"title": "Test Video", "views": 1000}, ttl=60)
    val, is_neg = await cache.get_with_status("test_key")
    assert val == {"title": "Test Video", "views": 1000}
    assert is_neg is False
    assert await cache.get("test_key") == {"title": "Test Video", "views": 1000}

    # 2. Negative cache
    await cache.set_negative("neg_key", reason="No captions available", ttl=60)
    val_neg, is_neg2 = await cache.get_with_status("neg_key")
    assert is_neg2 is True
    assert val_neg == {"__negative__": True, "reason": "No captions available"}
    assert await cache.get("neg_key") is None  # get() returns None on negative hit

    # 3. Delete
    assert await cache.delete("test_key") is True
    assert await cache.get("test_key") is None
    assert await cache.delete("non_existent_key") is False

    # 4. Clear
    await cache.set("k1", "v1")
    await cache.set("k2", "v2")
    await cache.clear()
    assert await cache.get("k1") is None
    assert await cache.get("k2") is None


@pytest.mark.asyncio
async def test_redis_malformed_json_recovery(caplog):
    """Verify that corrupt or non-JSON payloads in Redis are safely treated as cache misses."""
    cache = RedisCache("redis://localhost:6379/0")
    mock_client = AsyncMockRedisClient()
    cache._client = mock_client

    # Inject invalid JSON directly into the formatted key
    formatted_key = cache.format_key("corrupted_key")
    await mock_client.set(formatted_key, "{invalid json structure;;;")

    with caplog.at_level(logging.WARNING):
        val, is_neg = await cache.get_with_status("corrupted_key")
        assert val is None
        assert is_neg is False
        assert "malformed JSON" in caplog.text


@pytest.mark.asyncio
async def test_redis_connection_failure_graceful_degradation(caplog):
    """Verify that Redis connection errors degrade gracefully to cache miss without raising unhandled exceptions."""
    cache = RedisCache("redis://:secret_pass@unreachable-host:6379/0")
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Network unreachable")
    cache._client = mock_client

    with caplog.at_level(logging.WARNING):
        val, is_neg = await cache.get_with_status("search:query:en")
        assert val is None
        assert is_neg is False
        # Verify secrets are masked in the warning log
        assert "secret_pass" not in caplog.text
        assert "unreachable-host" in caplog.text


@pytest.mark.asyncio
async def test_redis_timeout_graceful_degradation():
    """Verify that Redis timeouts degrade gracefully."""
    cache = RedisCache("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_client.get.side_effect = TimeoutError("Redis socket timeout")
    cache._client = mock_client

    val = await cache.get("test_key")
    assert val is None
