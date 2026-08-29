import asyncio
import tempfile
import time
from typing import List
import pytest

from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.cache.memory import MemoryCache
from youtube_research_mcp.cache.redis import RedisCache
from youtube_research_mcp.cache.sqlite import SQLiteCache
from tests.unit.test_redis_production import AsyncMockRedisClient


@pytest.fixture
def sqlite_cache():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    cache = SQLiteCache(db_path)
    return cache


@pytest.fixture
def memory_cache():
    return MemoryCache()


@pytest.fixture
def redis_cache():
    cache = RedisCache("redis://localhost:6379/0")
    cache._client = AsyncMockRedisClient()
    return cache


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_missing_key(request, cache_fixture_name):
    """Parity Test 1: Missing key returns None and (None, False)."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)
    assert await cache.get("non_existent_key_123") is None
    val, is_neg = await cache.get_with_status("non_existent_key_123")
    assert val is None
    assert is_neg is False


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_positive_set_and_get(request, cache_fixture_name):
    """Parity Test 2 & 3: Positive set/get, complex payloads, and overwriting."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)
    payload = {
        "str": "hello",
        "int": 42,
        "list": [1, 2, 3],
        "nested": {"key": "val", "sublist": [{"a": 1}]},
    }
    await cache.set("complex_key", payload, ttl=100)

    val = await cache.get("complex_key")
    assert val == payload
    val_status, is_neg = await cache.get_with_status("complex_key")
    assert val_status == payload
    assert is_neg is False

    # Overwrite
    new_payload = {"overwritten": True}
    await cache.set("complex_key", new_payload, ttl=100)
    assert await cache.get("complex_key") == new_payload


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_negative_caching(request, cache_fixture_name):
    """Parity Test 4: Negative caching semantics across all backends."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)
    await cache.set_negative("uncaptioned_video", reason="No captions on YouTube", ttl=60)

    # get() must return None for negative cache hit
    assert await cache.get("uncaptioned_video") is None

    # get_with_status() must return positive is_negative flag
    val, is_neg = await cache.get_with_status("uncaptioned_video")
    assert is_neg is True
    assert isinstance(val, dict)
    assert "reason" in val


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_deletion_and_clear(request, cache_fixture_name):
    """Parity Test 5: Delete and clear across all backends."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)
    await cache.set("item_1", "value1")
    await cache.set("item_2", "value2")

    # Delete single key
    assert await cache.delete("item_1") is True
    assert await cache.get("item_1") is None
    assert await cache.delete("item_1") is False  # Second delete returns False

    # Clear all
    await cache.set("item_3", "value3")
    await cache.clear()
    assert await cache.get("item_2") is None
    assert await cache.get("item_3") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_key_isolation(request, cache_fixture_name):
    """Parity Test 6: Language and translation key isolation."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)
    # Different language and fallback parameters produce strictly isolated entries
    key_en = "transcript:vid1:en:None:None"
    key_hi = "transcript:vid1:hi:en:None"
    key_trans = "transcript:vid1:en:None:es"

    await cache.set(key_en, {"lang": "en"})
    await cache.set(key_hi, {"lang": "hi"})
    await cache.set(key_trans, {"lang": "es"})

    assert (await cache.get(key_en))["lang"] == "en"
    assert (await cache.get(key_hi))["lang"] == "hi"
    assert (await cache.get(key_trans))["lang"] == "es"


@pytest.mark.asyncio
@pytest.mark.parametrize("cache_fixture_name", ["sqlite_cache", "memory_cache", "redis_cache"])
async def test_cache_parity_concurrency(request, cache_fixture_name):
    """Parity Test 7: Concurrent writes and reads across all backends."""
    cache: BaseCache = request.getfixturevalue(cache_fixture_name)

    async def write_read(idx: int):
        k = f"concurrent_key_{idx}"
        await cache.set(k, {"idx": idx})
        res = await cache.get(k)
        assert res == {"idx": idx}

    tasks = [write_read(i) for i in range(20)]
    await asyncio.gather(*tasks)
