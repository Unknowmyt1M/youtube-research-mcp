import pytest
from unittest.mock import AsyncMock, MagicMock
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService


@pytest.mark.asyncio
async def test_innertube_android_profile_detects_captions_for_auto_caption_video():
    """Regression test for cQT33yu9pY8: Verify InnerTube get_video positively detects captions using the ANDROID client profile."""
    provider = InnerTubeProvider()

    # Call get_video directly for cQT33yu9pY8
    overview = await provider.get_video("cQT33yu9pY8")

    assert overview is not None
    assert overview.caption_available is True
    assert len(overview.available_languages) > 0
    assert "en" in overview.available_languages


@pytest.mark.asyncio
async def test_metadata_and_transcript_caption_consistency():
    """Verify MetadataService get_video_overview and TranscriptService get_transcript agree on caption presence."""
    meta_service = MetadataService()
    trans_service = TranscriptService()

    # Video cQT33yu9pY8
    overview = await meta_service.get_video_overview("cQT33yu9pY8")
    transcript = await trans_service.get_transcript("cQT33yu9pY8")

    assert overview is not None
    assert overview.caption_available is True
    assert transcript is not None
    assert transcript.actual_language in overview.available_languages or "en" in overview.available_languages


@pytest.mark.asyncio
async def test_genuine_no_caption_video_handling():
    """Verify that a video with no captions reports caption_available=False cleanly."""
    provider = InnerTubeProvider()

    # Mock response with playerCaptionsTracklistRenderer containing empty captionTracks
    mock_data = {
        "videoDetails": {
            "title": "No Caption Video",
            "author": "Test Author",
            "lengthSeconds": "60",
        },
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": []
            }
        }
    }

    overview = provider._parse_player_metadata(mock_data, "abc12345678")

    assert overview is not None
    assert overview.caption_available is False
    assert overview.available_languages == []
