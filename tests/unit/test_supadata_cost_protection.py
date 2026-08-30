import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from youtube_research_mcp.models.transcript import TranscriptResult, TranscriptSegment
from youtube_research_mcp.providers.base import ProviderCapability
from youtube_research_mcp.services.router import ProviderRouter

@pytest.mark.asyncio
async def test_no_captions_skips_commercial_fallback():
    """Verify that when free providers confirm a video has NO captions, Supadata is NEVER called."""
    router = ProviderRouter()
    
    # 1. YTA reports NoTranscriptFound
    router.yta.health.record_failure(ProviderCapability.TRANSCRIPT, "NoTranscriptFound: No captions found", is_systemic=False)
    
    with patch.object(router.yta, "get_transcript", new_callable=AsyncMock) as mock_yta, \
         patch.object(router.ytdlp, "get_transcript", new_callable=AsyncMock) as mock_ytdlp, \
         patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:
        
        mock_yta.return_value = None
        mock_ytdlp.return_value = None
        mock_inner.return_value = None
        
        res = await router.get_transcript(video_id="no_captions_vid", language="en")
        
        assert res is None
        # Assert Commercial Fallback (Supadata) was NEVER called, protecting quota!
        assert mock_comm.called is False

@pytest.mark.asyncio
async def test_network_block_triggers_commercial_fallback_as_last_resort():
    """Verify that when free providers fail due to IP block / 429, Supadata is invoked as last resort."""
    router = ProviderRouter()
    
    expected_result = TranscriptResult(
        video_id="blocked_vid",
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
                text="Hello world",
                timestamp_formatted="00:00",
                url="https://youtube.com/watch?v=blocked_vid&t=0s",
            )
        ],
        full_text="Hello world",
    )
    
    # Simulate YTA failing due to IpBlocked
    router.yta.health.record_failure(ProviderCapability.TRANSCRIPT, "IpBlocked: 429 Too Many Requests", is_systemic=True)
    
    with patch.object(router.yta, "get_transcript", new_callable=AsyncMock) as mock_yta, \
         patch.object(router.ytdlp, "get_transcript", new_callable=AsyncMock) as mock_ytdlp, \
         patch.object(router.innertube, "get_transcript", new_callable=AsyncMock) as mock_inner, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:
        
        mock_yta.return_value = None
        mock_ytdlp.return_value = None
        mock_inner.return_value = None
        mock_comm.return_value = expected_result
        
        res = await router.get_transcript(video_id="blocked_vid", language="en")
        
        assert res is not None
        assert res.video_id == "blocked_vid"
        # Assert free providers were tried first, then commercial fallback succeeded
        assert mock_yta.called
        assert mock_ytdlp.called
        assert mock_inner.called
        assert mock_comm.called

@pytest.mark.asyncio
async def test_free_provider_success_never_calls_commercial():
    """Verify that when a free provider succeeds, commercial fallback is NEVER called."""
    router = ProviderRouter()
    
    expected_result = TranscriptResult(
        video_id="free_success_vid",
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
                text="Free success",
                timestamp_formatted="00:00",
                url="https://youtube.com/watch?v=free_success_vid&t=0s",
            )
        ],
        full_text="Free success",
    )
    
    with patch.object(router.yta, "get_transcript", new_callable=AsyncMock) as mock_yta, \
         patch.object(router.commercial, "get_transcript", new_callable=AsyncMock) as mock_comm:
        
        mock_yta.return_value = expected_result
        
        res = await router.get_transcript(video_id="free_success_vid", language="en")
        
        assert res is not None
        assert res.full_text == "Free success"
        assert mock_yta.called
        assert mock_comm.called is False
