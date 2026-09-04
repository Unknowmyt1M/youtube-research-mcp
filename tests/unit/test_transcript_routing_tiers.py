import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import TranscriptResult, TranscriptSegment
from youtube_research_mcp.providers.base import ProviderCapability
from youtube_research_mcp.services.router import ProviderRouter
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.utils.metrics import metrics

def make_sample_transcript(video_id: str, provider: str = "youtube_transcript_api") -> TranscriptResult:
    return TranscriptResult(
        video_id=video_id,
        language="en",
        requested_language="en",
        actual_language="en",
        fallback_used=False,
        is_generated=False,
        is_translated=False,
        total_segments=1,
        total_words=5,
        duration_seconds=5.0,
        segments=[
            TranscriptSegment(
                start=0.0,
                duration=5.0,
                end=5.0,
                text="Sample caption",
                timestamp_formatted="00:00",
                url=f"https://youtube.com/watch?v={video_id}&t=0s",
            )
        ],
        full_text="Sample caption",
        provider=provider,
    )

@pytest.mark.asyncio
async def test_a_direct_free_success():
    """Test A: Direct free provider succeeds -> proxy not called -> Supadata not called."""
    router = ProviderRouter()
    expected = make_sample_transcript("vid_a", provider="youtube_transcript_api")

    with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:
        
        mock_yta.return_value = expected

        res = await router.get_transcript(video_id="vid_a", language="en")
        assert res is not None
        assert res.provider == "youtube_transcript_api"
        assert mock_yta.called
        assert mock_comm.called is False

@pytest.mark.asyncio
async def test_b_datacenter_blocked_proxy_succeeds():
    """Test B: Direct providers blocked (429) -> Proxied provider succeeds -> Supadata = 0."""
    with patch.object(settings, "RESIDENTIAL_PROXY_URL", "http://user:pass@proxy.residential.io:8080"):
        router = ProviderRouter()
        assert len(router.proxied_transcript_providers) == 2

        # Simulate direct providers failing with IpBlocked / 429
        router.yta_direct.health.record_failure(ProviderCapability.TRANSCRIPT, "IpBlocked: 429", is_systemic=True)
        router.ytdlp_direct.health.record_failure(ProviderCapability.TRANSCRIPT, "HTTP 429", is_systemic=True)
        router.innertube.health.record_failure(ProviderCapability.TRANSCRIPT, "HTTP 429", is_systemic=True)

        expected = make_sample_transcript("vid_b", provider="residential_proxy_youtube_transcript_api")

        with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta_dir, \
             patch.object(router.ytdlp_direct, "get_transcript", new_callable=AsyncMock) as mock_yt_dir, \
             patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
             patch.object(router.yta_proxied, "get_transcript", new_callable=AsyncMock) as mock_yta_proxy, \
             patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:

            mock_yta_dir.return_value = None
            mock_yt_dir.return_value = None
            mock_inner.return_value = None
            mock_yta_proxy.return_value = expected

            res = await router.get_transcript(video_id="vid_b", language="en")
            assert res is not None
            assert res.provider == "residential_proxy_youtube_transcript_api"
            assert mock_yta_proxy.called
            assert mock_comm.called is False

@pytest.mark.asyncio
async def test_c_all_free_fail_supadata_called_once():
    """Test C: All free direct and proxied routes fail due to network challenge -> Supadata called exactly once."""
    router = ProviderRouter()
    router.yta_direct.health.record_failure(ProviderCapability.TRANSCRIPT, "IpBlocked: 429", is_systemic=True)
    expected = make_sample_transcript("vid_c", provider="supadata")

    with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta_dir, \
         patch.object(router.ytdlp_direct, "get_transcript", new_callable=AsyncMock) as mock_yt_dir, \
         patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:

        mock_yta_dir.return_value = None
        mock_yt_dir.return_value = None
        mock_inner.return_value = None
        mock_comm.return_value = expected

        res = await router.get_transcript(video_id="vid_c", language="en")
        assert res is not None
        assert res.provider == "supadata"
        assert mock_comm.call_count == 1

@pytest.mark.asyncio
async def test_d_cache_hit_zero_upstream_calls():
    """Test D: Cached transcript -> zero upstream provider calls -> Supadata = 0."""
    service = TranscriptService()
    sample = make_sample_transcript("dQw4w9WgXcQ", provider="youtube_transcript_api")

    with patch.object(service.cache, "get_with_status", new_callable=AsyncMock) as mock_get_cache, \
         patch.object(service.router, "get_transcript", new_callable=AsyncMock) as mock_router:

        mock_get_cache.return_value = (sample.model_dump(), False)

        res = await service.get_transcript(video_id_or_url="dQw4w9WgXcQ", language="en")
        assert res is not None
        assert res.video_id == "dQw4w9WgXcQ"
        assert mock_router.called is False

@pytest.mark.asyncio
async def test_e_invalid_video_supadata_zero():
    """Test E: Invalid video ID -> fast validation fail -> Supadata = 0."""
    service = TranscriptService()

    with patch.object(service.router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:
        # Invalid short string should raise or be handled
        with pytest.raises(Exception):
            await service.get_transcript(video_id_or_url="short_bad_id", language="en")
        assert mock_comm.called is False

@pytest.mark.asyncio
async def test_f_no_captions_confirmed_supadata_zero():
    """Test F: Verified content absence (NoTranscriptFound) -> Cost guard stops call -> Supadata = 0."""
    router = ProviderRouter()
    router.yta_direct.health.record_failure(ProviderCapability.TRANSCRIPT, "NoTranscriptFound: No captions found", is_systemic=False)

    with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta, \
         patch.object(router.ytdlp_direct, "get_transcript", new_callable=AsyncMock) as mock_ytdlp, \
         patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:

        mock_yta.return_value = None
        mock_ytdlp.return_value = None
        mock_inner.return_value = None

        res = await router.get_transcript(video_id="no_captions_vid", language="en")
        assert res is None
        assert mock_comm.called is False

@pytest.mark.asyncio
async def test_g_concurrent_duplicate_single_flight():
    """Test G: 10 concurrent duplicate requests coalesced by SingleFlight -> exactly 1 upstream execution."""
    router = ProviderRouter()
    expected = make_sample_transcript("concurrent_vid", provider="youtube_transcript_api")

    with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta:
        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(0.05)
            return expected

        mock_yta.side_effect = slow_fetch

        tasks = [
            router.get_transcript(video_id="concurrent_vid", language="en")
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r is not None and r.video_id == "concurrent_vid" for r in results)
        assert mock_yta.call_count == 1

@pytest.mark.asyncio
async def test_h_supadata_daily_quota_limit():
    """Test H: SUPADATA_MAX_DAILY_REQUESTS cap enforces daily limits strictly without extra calls."""
    with patch.object(settings, "SUPADATA_MAX_DAILY_REQUESTS", 2):
        router = ProviderRouter()
        router.yta_direct.health.record_failure(ProviderCapability.TRANSCRIPT, "IpBlocked: 429", is_systemic=True)

        with patch.object(router.yta_direct, "get_transcript", new_callable=AsyncMock) as mock_yta, \
             patch.object(router.ytdlp_direct, "get_transcript", new_callable=AsyncMock) as mock_ytdlp, \
             patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
             patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:

            mock_yta.return_value = None
            mock_ytdlp.return_value = None
            mock_inner.return_value = None
            mock_comm.side_effect = lambda video_id, **kw: make_sample_transcript(video_id, provider="supadata")

            # Request 1: Allowed (call 1)
            r1 = await router.get_transcript(video_id="vid_1", language="en")
            assert r1 is not None and r1.provider == "supadata"
            assert router.supadata_daily_calls == 1

            # Request 2: Allowed (call 2)
            r2 = await router.get_transcript(video_id="vid_2", language="en")
            assert r2 is not None and r2.provider == "supadata"
            assert router.supadata_daily_calls == 2

            # Request 3: Cap Exceeded -> Reject commercial fallback
            r3 = await router.get_transcript(video_id="vid_3", language="en")
            assert r3 is None
            assert router.supadata_daily_calls == 2
            assert mock_comm.call_count == 2

@pytest.mark.asyncio
async def test_supadata_multi_key_failover():
    """Test multi-key failover when Key 1 returns 429/402 and Key 2 or Key 3 succeeds."""
    from youtube_research_mcp.providers.commercial import CommercialProvider
    import httpx

    with patch.object(settings, "SUPADATA_API_KEY", "key_1_exhausted"), \
         patch.object(settings, "SUPADATA_API_KEY_SECONDARY", "mock_key_2_valid"), \
         patch.object(settings, "SUPADATA_API_KEY_TERTIARY", "mock_key_3_valid"):

        provider = CommercialProvider()
        mock_client = AsyncMock()

        async def mock_get(url, headers=None):
            api_key = headers.get("x-api-key") if headers else None
            if api_key == "key_1_exhausted":
                return httpx.Response(429, json={"message": "Quota exceeded"})
            elif api_key == "mock_key_2_valid":
                return httpx.Response(200, json={
                    "lang": "en",
                    "content": [{"offset": 0, "duration": 5000, "text": "Failover success"}]
                })
            return httpx.Response(400)

        mock_client.get.side_effect = mock_get

        with patch.object(provider, "get_client", new_callable=AsyncMock) as mock_get_client:
            mock_get_client.return_value = mock_client
            res = await provider.get_transcript(video_id="dQw4w9WgXcQ", language="en")
            assert res is not None
            assert res.provider == "supadata"
            assert res.full_text == "Failover success"
            assert mock_client.get.call_count == 2
