import pytest
from unittest.mock import AsyncMock, patch

from youtube_research_mcp.cache import get_cache, reset_cache
from youtube_research_mcp.cache.redis import RedisCache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService
from tests.unit.test_redis_production import AsyncMockRedisClient


@pytest.fixture(autouse=True)
def configure_redis_backend():
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CACHE_BACKEND", "redis")
        mp.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        reset_cache()
        cache = get_cache()
        assert isinstance(cache, RedisCache)
        cache._client = AsyncMockRedisClient()
        yield cache
        reset_cache()


@pytest.mark.asyncio
async def test_search_service_with_redis_cache_hit():
    """Verify search caching in Redis: 1st request -> upstream fetch & store in Redis; 2nd request -> cache hit."""
    service = SearchService()
    mock_results = [
        VideoSearchResult(
            video_id="dQw4w9WgXcQ",
            title="Rick Astley - Never Gonna Give You Up",
            channel="RickAstleyVEVO",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
    ]

    with patch.object(service.router, "search", new_callable=AsyncMock) as mock_router_search:
        mock_router_search.return_value = mock_results

        # Request 1: Cache miss -> upstream call
        resp1 = await service.search(query="never gonna give you up", max_results=5)
        assert len(resp1.results) == 1
        assert resp1.results[0].video_id == "dQw4w9WgXcQ"
        assert mock_router_search.call_count == 1

        # Request 2: Cache hit from Redis -> no router call
        resp2 = await service.search(query="never gonna give you up", max_results=5)
        assert len(resp2.results) == 1
        assert resp2.results[0].video_id == "dQw4w9WgXcQ"
        assert mock_router_search.call_count == 1  # Still 1!


@pytest.mark.asyncio
async def test_transcript_service_with_redis_negative_caching():
    """Verify transcript uncaptioned videos are stored as negative cache in Redis."""
    service = TranscriptService()

    with patch.object(service.router, "get_transcript", new_callable=AsyncMock) as mock_get_transcript:
        mock_get_transcript.return_value = None  # No transcript available

        # 1st call -> router called -> stores negative entry in Redis
        res1 = await service.get_transcript("dQw4w9WgXcQ", language="en")
        assert res1 is None
        assert mock_get_transcript.call_count == 1

        # 2nd call -> immediate negative hit from Redis
        res2 = await service.get_transcript("dQw4w9WgXcQ", language="en")
        assert res2 is None
        assert mock_get_transcript.call_count == 1  # Still 1!


@pytest.mark.asyncio
async def test_mcp_service_graceful_degradation_when_redis_fails():
    """Verify that if Redis throws connection errors during search, SearchService continues via upstream."""
    service = SearchService()
    mock_results = [
        VideoSearchResult(
            video_id="dQw4w9WgXcQ",
            title="Rick Astley - Never Gonna Give You Up",
            channel="RickAstleyVEVO",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
    ]

    # Inject connection error into Redis client
    mock_failing_client = AsyncMock()
    mock_failing_client.get.side_effect = ConnectionError("Redis server down")
    mock_failing_client.set.side_effect = ConnectionError("Redis server down")
    service.cache._client = mock_failing_client

    with patch.object(service.router, "search", new_callable=AsyncMock) as mock_router_search:
        mock_router_search.return_value = mock_results

        # Should NOT raise exception; should degrade gracefully and return upstream results
        resp = await service.search(query="resilience test query", max_results=5)
        assert len(resp.results) == 1
        assert resp.results[0].video_id == "dQw4w9WgXcQ"
        assert mock_router_search.call_count == 1
