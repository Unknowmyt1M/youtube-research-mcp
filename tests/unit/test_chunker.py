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


def test_chunker_handles_punctuation_free_auto_generated_captions():
    chunker = TranscriptChunker(target_words=20, overlap_words=5)
    # Target safety threshold will be int(20 * 1.5) = 30 words.
    # We pass 50 unpunctuated words across 5 segments (10 words each).
    segments = []
    for i in range(5):
        segments.append(
            TranscriptSegment(
                start=float(i * 5),
                duration=5.0,
                end=float((i + 1) * 5),
                text=f"unpunctuated segment number {i+1} with extra words to exceed safety threshold",
                timestamp_formatted=f"00:0{i*5}",
                url=f"https://youtu.be/testasr1234?t={i*5}",
            )
        )

    chunks = chunker.chunk_transcript("testasr1234", segments)

    # Should break into multiple chunks despite having zero punctuation (',', '.', '!', '?')
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text.split()) <= 40

