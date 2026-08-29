import asyncio
import pytest
from unittest.mock import patch
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider
from youtube_research_mcp.providers.base import ProviderCapability
from youtube_research_mcp.config import settings


@pytest.mark.asyncio
async def test_ytdlp_timeout_fails_gracefully():
    """Verify that when yt-dlp hangs, it times out and records failure on circuit breaker."""
    provider = YtDlpProvider()

    async def hanging_thread(*args, **kwargs):
        await asyncio.sleep(5.0)
        return {}

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "REQUEST_TIMEOUT", 0.05)
        with patch("asyncio.to_thread", side_effect=hanging_thread):
            res = await provider.search("query that hangs", max_results=5)
            assert res == []

            # Circuit breaker should record failure
            breaker = provider.health.breakers[ProviderCapability.SEARCH]
            assert breaker.failure_count >= 1
