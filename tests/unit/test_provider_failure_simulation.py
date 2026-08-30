import asyncio
import httpx
from unittest.mock import AsyncMock, patch
import pytest

from youtube_research_mcp.providers.base import ProviderCapability
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider
from youtube_research_mcp.providers.commercial import CommercialProvider
from youtube_research_mcp.services.router import ProviderRouter


@pytest.mark.asyncio
async def test_innertube_http_500_and_429_failure_simulation():
    """Verify InnerTube records failure on HTTP 500/429 and transitions circuit breaker properly."""
    provider = InnerTubeProvider()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # 1. HTTP 500 Internal Server Error
    resp_500 = AsyncMock(spec=httpx.Response)
    resp_500.status_code = 500
    mock_client.post.return_value = resp_500

    with patch.object(provider, "get_client", return_value=mock_client):
        res = await provider.search("test query")
        assert res == []
        assert provider.health.breakers[ProviderCapability.SEARCH].failure_count == 1

        # 2. Repeated HTTP 429 trips circuit
        resp_429 = AsyncMock(spec=httpx.Response)
        resp_429.status_code = 429
        mock_client.post.return_value = resp_429

        await provider.search("test query 2")
        await provider.search("test query 3")

        # After 3 failures, circuit is tripped
        assert provider.health.can_execute(ProviderCapability.SEARCH) is False


@pytest.mark.asyncio
async def test_innertube_malformed_json_and_partial_data_simulation():
    """Verify InnerTube handles malformed JSON and corrupted payloads gracefully."""
    provider = InnerTubeProvider()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_200 = AsyncMock(spec=httpx.Response)
    resp_200.status_code = 200
    # Malformed response structure without expected sections
    resp_200.json.return_value = {"contents": "corrupted_non_dict"}
    mock_client.post.return_value = resp_200

    with patch.object(provider, "get_client", return_value=mock_client):
        res = await provider.search("test query")
        assert res == []


@pytest.mark.asyncio
async def test_router_failover_when_tier1_provider_fails():
    """Verify router automatically fails over to Tier 2 when Tier 1 provider fails or times out."""
    router = ProviderRouter()

    # Make InnerTube search fail
    with patch.object(router.innertube, "search", new_callable=AsyncMock) as mock_inner:
        mock_inner.return_value = []  # Empty/fail

        # Make YtDlp succeed
        from youtube_research_mcp.models.search import VideoSearchResult
        expected = [
            VideoSearchResult(
                video_id="dQw4w9WgXcQ",
                title="YtDlp Fallback Title",
                channel="YtDlp Channel",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )
        ]

        with patch.object(router.ytdlp, "search", new_callable=AsyncMock) as mock_ytdlp:
            mock_ytdlp.return_value = expected

            results = await router.search("test failover query")
            assert len(results) == 1
            assert results[0].title == "YtDlp Fallback Title"
            assert mock_inner.called
            assert mock_ytdlp.called
