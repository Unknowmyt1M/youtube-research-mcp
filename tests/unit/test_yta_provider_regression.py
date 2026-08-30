import pytest
from unittest.mock import MagicMock, patch
from youtube_research_mcp.providers.youtube_transcript_api_provider import YouTubeTranscriptApiProvider
from youtube_research_mcp.models.transcript import TranscriptResult
from youtube_transcript_api._errors import IpBlocked, NoTranscriptFound, VideoUnavailable


@pytest.mark.asyncio
async def test_yta_provider_candidate_fallback_on_first_failure():
    """Verify YouTubeTranscriptApiProvider tries next candidate if the first candidate fails."""
    provider = YouTubeTranscriptApiProvider()

    # Mock manual track (fails with IpBlocked)
    mock_manual = MagicMock()
    mock_manual.language_code = "en"
    mock_manual.is_generated = False
    mock_manual.is_translatable = True
    mock_manual.fetch.side_effect = IpBlocked("dQw4w9WgXcQ")

    # Mock generated track (succeeds)
    mock_gen = MagicMock()
    mock_gen.language_code = "en"
    mock_gen.is_generated = True
    mock_gen.is_translatable = True
    mock_gen.fetch.return_value = [
        {"text": "Quantum computers use qubits", "start": 0.0, "duration": 2.5}
    ]

    mock_list = MagicMock()
    mock_list._manually_created_transcripts = {"en": mock_manual}
    mock_list._generated_transcripts = {"en": mock_gen}
    mock_list.__iter__.return_value = [mock_manual, mock_gen]

    mock_api = MagicMock()
    mock_api.list.return_value = mock_list
    provider._api = mock_api

    res = await provider.get_transcript(video_id="dQw4w9WgXcQ", language="en")

    assert res is not None
    assert res.total_segments == 1
    assert res.segments[0].text == "Quantum computers use qubits"
    assert res.language == "en"
    assert res.is_generated is True


@pytest.mark.asyncio
async def test_yta_provider_translation():
    """Verify YouTubeTranscriptApiProvider translates translatable captions."""
    provider = YouTubeTranscriptApiProvider()

    mock_source = MagicMock()
    mock_source.language_code = "en"
    mock_source.is_generated = False
    mock_source.is_translatable = True

    mock_translated = MagicMock()
    mock_translated.language_code = "hi"
    mock_translated.is_generated = False
    mock_translated.is_translatable = True
    mock_translated.fetch.return_value = [
        {"text": "क्वांटम कंप्यूटर क्यूबिट्स का उपयोग करते हैं", "start": 0.0, "duration": 2.5}
    ]

    mock_source.translate.return_value = mock_translated

    mock_list = MagicMock()
    mock_list._manually_created_transcripts = {"en": mock_source}
    mock_list._generated_transcripts = {}
    mock_list.__iter__.return_value = [mock_source]

    mock_api = MagicMock()
    mock_api.list.return_value = mock_list
    provider._api = mock_api

    res = await provider.get_transcript(video_id="dQw4w9WgXcQ", language="en", translate_to="hi")

    assert res is not None
    assert res.is_translated is True
    assert res.actual_language == "hi"
    assert res.segments[0].text == "क्वांटम कंप्यूटर क्यूबिट्स का उपयोग करते हैं"


@pytest.mark.asyncio
async def test_yta_provider_clean_error_handling():
    """Verify provider does not raise unhandled TypeErrors on error recording."""
    provider = YouTubeTranscriptApiProvider()

    mock_api = MagicMock()
    mock_api.list.side_effect = VideoUnavailable("dQw4w9WgXcQ")
    provider._api = mock_api

    res = await provider.get_transcript(video_id="dQw4w9WgXcQ", language="en")
    assert res is None

    mock_api.list.side_effect = IpBlocked("dQw4w9WgXcQ")
    res_blocked = await provider.get_transcript(video_id="dQw4w9WgXcQ", language="en")
    assert res_blocked is None
