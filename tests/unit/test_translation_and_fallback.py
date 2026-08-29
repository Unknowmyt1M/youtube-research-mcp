import pytest
from unittest.mock import AsyncMock, MagicMock
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.services.transcripts import TranscriptService


@pytest.mark.asyncio
async def test_innertube_fallback_and_translation():
    """Verify InnerTubeProvider handles fallback language and translate_to parameter."""
    provider = InnerTubeProvider()

    player_data = {
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "languageCode": "en",
                        "name": {"runs": [{"text": "English"}]},
                        "baseUrl": "https://www.youtube.com/api/timedtext?v=test&lang=en",
                        "kind": "asr",
                    }
                ]
            }
        }
    }

    mock_client = AsyncMock()
    mock_client.is_closed = False

    # Mock POST for player metadata and GET for timedtext
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = player_data

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "events": [
            {
                "tStartMs": 0,
                "dDurationMs": 2000,
                "segs": [{"utf8": "Hello translated world"}],
            }
        ]
    }

    mock_client.post.return_value = mock_post_resp
    mock_client.get.return_value = mock_get_resp
    provider._client = mock_client

    # Request Hindi with English fallback & translate to Spanish
    res = await provider.get_transcript(
        video_id="dQw4w9WgXcQ",
        language="hi",
        fallback_language="en",
        translate_to="es",
    )

    assert res is not None
    assert res.requested_language == "hi"
    assert res.fallback_used is True
    assert res.fallback_language == "en"
    assert res.actual_language == "es"
    assert res.is_translated is True

    # Check timedtext URL included &tlang=es
    call_url = mock_client.get.call_args[0][0]
    assert "&tlang=es" in call_url


@pytest.mark.asyncio
async def test_transcript_service_cache_isolation():
    """Verify cache keys for translated and untranslated requests remain strictly isolated."""
    service = TranscriptService()
    mock_cache = AsyncMock()
    mock_cache.get_with_status.return_value = (None, False)
    service.cache = mock_cache

    mock_router = AsyncMock()
    mock_router.get_transcript.return_value = None
    service.router = mock_router

    # Untranslated request
    await service.get_transcript("dQw4w9WgXcQ", language="en", fallback_language="en", translate_to=None)
    untrans_key = mock_cache.get_with_status.call_args[0][0]
    assert "transcript:dQw4w9WgXcQ:en:en:None" == untrans_key

    # Translated request
    await service.get_transcript("dQw4w9WgXcQ", language="en", fallback_language="en", translate_to="es")
    trans_key = mock_cache.get_with_status.call_args[0][0]
    assert "transcript:dQw4w9WgXcQ:en:en:es" == trans_key

    # Ensure keys are distinct
    assert untrans_key != trans_key
