import asyncio
import os
import time
from typing import Optional
from unittest.mock import AsyncMock, patch
import pytest

from youtube_research_mcp.cache import reset_cache
from youtube_research_mcp.cache.redis import RedisCache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.services.search import SearchService


async def detect_live_redis() -> Optional[str]:
    """Probe candidates for a reachable live Redis server using protocol=2."""
    candidates = [
        os.getenv("TEST_REDIS_URL"),
        os.getenv("REDIS_URL"),
        "redis://localhost:6380/0",
        "redis://localhost:6379/0",
    ]
    import redis.asyncio as aioredis

    for url in candidates:
        if not url:
            continue
        try:
            r = aioredis.from_url(url, protocol=2, socket_timeout=1.0, socket_connect_timeout=1.0)
            await r.ping()
            await r.aclose()
            return url
        except Exception:
            continue
    return None


@pytest.fixture(scope="module")
def live_redis_url():
    """Module-level fixture to discover and provide active live Redis URL or skip."""
    url = asyncio.run(detect_live_redis())
    if not url:
        pytest.skip("REAL REDIS: NOT AVAILABLE (No live Redis server reachable on localhost:6380, localhost:6379, or REDIS_URL)")
    return url


@pytest.fixture
async def real_redis_cache(live_redis_url):
    """Instantiate and yield a real RedisCache connected to the live Redis server, cleaning test keys after."""
    cache = RedisCache(redis_url=live_redis_url)
    # Ensure fresh state
    await cache.clear()
    yield cache
    await cache.clear()
    await cache.close()


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_ping_and_connection(live_redis_url, real_redis_cache):
    """Verify live connection establishment, ping, and client info on real Redis."""
    client = await real_redis_cache._get_client()
    pong = await client.ping()
    assert pong is True
    info = await client.info()
    assert "redis_version" in info
    assert len(info["redis_version"]) > 0


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_positive_cache_lifecycle(real_redis_cache):
    """Verify MISS -> SET -> HIT -> DELETE -> MISS lifecycle on real Redis server."""
    test_key = "live_test:video:dQw4w9WgXcQ"
    payload = {"video_id": "dQw4w9WgXcQ", "title": "Live Test Video", "views": 42000}

    # 1. Initial MISS
    assert await real_redis_cache.get(test_key) is None
    val, is_neg = await real_redis_cache.get_with_status(test_key)
    assert val is None
    assert is_neg is False

    # 2. SET
    await real_redis_cache.set(test_key, payload, ttl=120)

    # 3. HIT
    cached = await real_redis_cache.get(test_key)
    assert cached == payload
    cached_val, is_neg_hit = await real_redis_cache.get_with_status(test_key)
    assert cached_val == payload
    assert is_neg_hit is False

    # 4. DELETE
    deleted = await real_redis_cache.delete(test_key)
    assert deleted is True

    # 5. Post-delete MISS
    assert await real_redis_cache.get(test_key) is None


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_negative_caching_and_ttl(real_redis_cache):
    """Verify negative caching, live TTL on Redis server, and get_with_status semantics."""
    test_key = "live_test:nocaptions:video_abc123"

    # 1. Store negative entry
    await real_redis_cache.set_negative(test_key, reason="Captions are disabled by creator", ttl=60)

    # 2. get() must return None for negative hit
    assert await real_redis_cache.get(test_key) is None

    # 3. get_with_status() must return is_negative = True and reason payload
    val, is_neg = await real_redis_cache.get_with_status(test_key)
    assert is_neg is True
    assert isinstance(val, dict)
    assert "Captions are disabled" in val["reason"]

    # 4. Check native Redis TTL directly from server
    client = await real_redis_cache._get_client()
    formatted_key = real_redis_cache.format_key(test_key)
    server_ttl = await client.ttl(formatted_key)
    assert server_ttl > 0
    assert server_ttl <= 60


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_key_and_language_isolation(real_redis_cache):
    """Verify that different languages, fallbacks, and translations remain strictly isolated in real Redis."""
    key_en = "transcript:live_vid:en:None:None"
    key_es = "transcript:live_vid:es:en:None"
    key_hi = "transcript:live_vid:hi:None:None"

    await real_redis_cache.set(key_en, {"lang": "en", "text": "Hello"})
    await real_redis_cache.set(key_es, {"lang": "es", "text": "Hola"})
    await real_redis_cache.set(key_hi, {"lang": "hi", "text": "Namaste"})

    res_en = await real_redis_cache.get(key_en)
    res_es = await real_redis_cache.get(key_es)
    res_hi = await real_redis_cache.get(key_hi)

    assert res_en["lang"] == "en"
    assert res_es["lang"] == "es"
    assert res_hi["lang"] == "hi"


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_clear_namespace_isolation(real_redis_cache):
    """Verify that clear() only deletes keys matching the active version prefix and preserves external keys."""
    client = await real_redis_cache._get_client()

    # 1. Set a sentinel key OUTSIDE the application's versioned namespace
    sentinel_key = "youtube-research:test:sentinel_survivor"
    await client.set(sentinel_key, "keep_me_alive", ex=120)

    # 2. Set an application key inside the versioned namespace
    app_key = "test_app_item_1"
    await real_redis_cache.set(app_key, {"status": "to_be_cleared"})

    # 3. Call clear()
    await real_redis_cache.clear()

    # 4. App key is gone, sentinel key survives
    assert await real_redis_cache.get(app_key) is None
    sentinel_val = await client.get(sentinel_key)
    assert sentinel_val == "keep_me_alive"

    # Cleanup sentinel
    await client.delete(sentinel_key)


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_malformed_json_resilience(real_redis_cache):
    """Verify that corrupted JSON stored in live Redis is safely handled as a cache miss without crashing."""
    client = await real_redis_cache._get_client()
    formatted_key = real_redis_cache.format_key("corrupt_live_key")

    # Write raw unparseable string directly to Redis
    await client.set(formatted_key, "THIS_IS_NOT_JSON_<<<>>>", ex=60)

    val, is_neg = await real_redis_cache.get_with_status("corrupt_live_key")
    assert val is None
    assert is_neg is False
    assert await real_redis_cache.get("corrupt_live_key") is None


@pytest.mark.redis
@pytest.mark.asyncio
async def test_real_redis_mcp_search_service_e2e(live_redis_url):
    """End-to-End Real Redis Test: SearchService -> Cache Factory -> RedisCache -> Real Redis Server."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CACHE_BACKEND", "redis")
        mp.setattr(settings, "REDIS_URL", live_redis_url)
        reset_cache()

        service = SearchService()
        assert isinstance(service.cache, RedisCache)
        await service.cache.clear()

        mock_results = [
            VideoSearchResult(
                video_id="dQw4w9WgXcQ",
                title="Rick Astley Live Real Redis",
                channel="RickAstleyVEVO",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )
        ]

        with patch.object(service.router, "search", new_callable=AsyncMock) as mock_router:
            mock_router.return_value = mock_results

            # 1. Request 1: Cache miss -> calls router -> stores in Real Redis
            resp1 = await service.search(query="live real redis test", max_results=5)
            assert len(resp1.results) == 1
            assert resp1.results[0].title == "Rick Astley Live Real Redis"
            assert mock_router.call_count == 1

            # 2. Request 2: Cache hit from Real Redis -> 0 router calls
            resp2 = await service.search(query="live real redis test", max_results=5)
            assert len(resp2.results) == 1
            assert resp2.results[0].title == "Rick Astley Live Real Redis"
            assert mock_router.call_count == 1  # Still 1!

        await service.cache.clear()
        reset_cache()
