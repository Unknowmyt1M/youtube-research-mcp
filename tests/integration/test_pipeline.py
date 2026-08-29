import pytest
from youtube_research_mcp.models.research import ResearchDepth
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.services.research import ResearchEngine


@pytest.mark.asyncio
async def test_search_service_live():
    search_service = SearchService()
    resp = await search_service.search("quantum computing 3blue1brown", max_results=3)

    assert resp.total_results > 0
    assert len(resp.results) > 0
    first = resp.results[0]
    assert len(first.video_id) == 11
    assert first.title
    assert "https://www.youtube.com/watch?v=" in first.url


@pytest.mark.asyncio
async def test_metadata_service_live():
    metadata_service = MetadataService()
    overview = await metadata_service.get_video_overview("dQw4w9WgXcQ")

    assert overview is not None
    assert overview.video_id == "dQw4w9WgXcQ"
    assert "Rick" in overview.title or "Never Gonna Give You Up" in overview.title
    assert overview.channel


@pytest.mark.asyncio
async def test_transcript_and_find_in_video_live():
    transcript_service = TranscriptService()
    video_id = "dQw4w9WgXcQ"

    transcript = await transcript_service.get_transcript(video_id, language="en")
    if transcript:
        assert transcript.video_id == "dQw4w9WgXcQ"
        assert len(transcript.segments) > 0
        assert transcript.total_words > 0
        assert transcript.requested_language == "en"
        assert transcript.actual_language in ["en", "en-US", "en-GB", "en-orig"]

        # Test pinpoint search in video
        matches = await transcript_service.find_in_video(
            video_id=video_id, query="never gonna give you up", max_results=2
        )
        assert len(matches) > 0
        assert matches[0].url.startswith("https://youtu.be/dQw4w9WgXcQ?t=")


@pytest.mark.asyncio
async def test_multi_video_research_engine_live():
    research_engine = ResearchEngine()
    result = await research_engine.research_topic(
        query="what is quantum computing", depth=ResearchDepth.QUICK
    )

    assert result.topic == "what is quantum computing"
    assert result.depth == ResearchDepth.QUICK
    assert result.total_videos_analyzed == 2
    assert len(result.sources) == 2
