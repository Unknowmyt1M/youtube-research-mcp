import pytest
from youtube_research_mcp.models.transcript import TranscriptResult, TranscriptSegment


def test_transcript_result_language_provenance():
    # 1. Exact match (no fallback)
    res_exact = TranscriptResult(
        video_id="test1111111",
        language="hi",
        requested_language="hi",
        actual_language="hi",
        fallback_used=False,
        fallback_language=None,
        is_generated=False,
        is_translated=False,
        total_segments=1,
        total_words=2,
        duration_seconds=5.0,
        segments=[
            TranscriptSegment(
                start=0.0,
                duration=5.0,
                end=5.0,
                text="नमस्ते दुनिया",
                timestamp_formatted="00:00",
                url="https://youtu.be/test1111111?t=0",
            )
        ],
        full_text="नमस्ते दुनिया",
    )

    assert res_exact.requested_language == "hi"
    assert res_exact.actual_language == "hi"
    assert res_exact.fallback_used is False

    # 2. Fallback used
    res_fallback = TranscriptResult(
        video_id="test2222222",
        language="en",
        requested_language="hi",
        actual_language="en",
        fallback_used=True,
        fallback_language="en",
        is_generated=True,
        is_translated=False,
        total_segments=1,
        total_words=2,
        duration_seconds=5.0,
        segments=[
            TranscriptSegment(
                start=0.0,
                duration=5.0,
                end=5.0,
                text="Hello World",
                timestamp_formatted="00:00",
                url="https://youtu.be/test2222222?t=0",
            )
        ],
        full_text="Hello World",
    )

    assert res_fallback.requested_language == "hi"
    assert res_fallback.actual_language == "en"
    assert res_fallback.fallback_used is True
    assert res_fallback.fallback_language == "en"
