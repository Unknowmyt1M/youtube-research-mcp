from youtube_research_mcp.models.transcript import TranscriptSegment
from youtube_research_mcp.models.video import Chapter
from youtube_research_mcp.services.chunker import TranscriptChunker


def test_chunker_merges_segments_and_preserves_timestamps():
    chunker = TranscriptChunker(target_words=20, overlap_words=5)

    segments = [
        TranscriptSegment(
            start=0.0,
            duration=3.0,
            end=3.0,
            text="Hello and welcome to this deep dive on artificial intelligence.",
            timestamp_formatted="00:00",
            url="https://youtu.be/test1234567?t=0",
        ),
        TranscriptSegment(
            start=3.0,
            duration=4.0,
            end=7.0,
            text="Today we will discuss large language models and autonomous coding agents.",
            timestamp_formatted="00:03",
            url="https://youtu.be/test1234567?t=3",
        ),
        TranscriptSegment(
            start=7.0,
            duration=5.0,
            end=12.0,
            text="Neural networks have evolved rapidly over the past few years.",
            timestamp_formatted="00:07",
            url="https://youtu.be/test1234567?t=7",
        ),
    ]

    chapters = [
        Chapter(
            title="Introduction to LLMs",
            start_seconds=0.0,
            end_seconds=15.0,
            timestamp_formatted="00:00",
            url="https://youtu.be/test1234567?t=0",
        )
    ]

    chunks = chunker.chunk_transcript("test1234567", segments, chapters=chapters)

    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert first_chunk.video_id == "test1234567"
    assert first_chunk.start_seconds == 0.0
    assert first_chunk.end_seconds >= 7.0
    assert "artificial intelligence" in first_chunk.text
    assert first_chunk.chapter_title == "Introduction to LLMs"
    assert "https://youtu.be/test1234567?t=" in first_chunk.url
