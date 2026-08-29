import asyncio
import pytest
from youtube_research_mcp.cache.memory import MemoryCache


@pytest.mark.asyncio
async def test_memory_cache_lifecycle():
    """Verify set, get, get_with_status, negative caching, max entries, and clear on MemoryCache."""
    cache = MemoryCache(max_entries=3)

    # 1. Positive set and get
    await cache.set("k1", {"data": "v1"}, ttl=60)
    val, is_neg = await cache.get_with_status("k1")
    assert val == {"data": "v1"}
    assert is_neg is False
    assert await cache.get("k1") == {"data": "v1"}

    # 2. Negative caching
    await cache.set_negative("k_neg", reason="not found", ttl=60)
    val_neg, is_neg2 = await cache.get_with_status("k_neg")
    assert is_neg2 is True
    assert await cache.get("k_neg") is None  # get() returns None on negative hit

    # 3. Max entries eviction
    await cache.set("k2", "v2", ttl=60)
    await cache.set("k3", "v3", ttl=60)
    await cache.set("k4", "v4", ttl=60)
    # Cache capacity was 3, so oldest entries get evicted
    assert len(cache._store) <= 3

    # 4. Clear
    await cache.clear()
    assert len(cache._store) == 0
