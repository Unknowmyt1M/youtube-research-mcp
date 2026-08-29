import asyncio
import pytest
from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import RetrievalIndexCache


@pytest.mark.asyncio
async def test_concurrent_retrieval_index_build_once():
    """Verify that multiple concurrent calls to get_or_build for the same video build the index only once."""
    cache = RetrievalIndexCache(max_size=10, ttl_seconds=60)
    chunks = [
        TranscriptChunk(
            chunk_id="c1",
            video_id="test_vid_11",
            start_seconds=0.0,
            end_seconds=10.0,
            time_range="00:00 - 00:10",
            text="First sentence for testing concurrency.",
            word_count=5,
            url="https://youtu.be/test_vid_11?t=0",
        )
    ]

    # Spawn 10 concurrent requests for the same video_id
    tasks = [cache.get_or_build("test_vid_11", chunks) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All 10 callers should receive the exact same index instance
    first_index = results[0]
    for idx in results[1:]:
        assert idx is first_index
