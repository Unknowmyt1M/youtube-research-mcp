import pytest
from pydantic import ValidationError

from youtube_research_mcp.models.research import (
    DEPTH_CITATIONS_PER_VIDEO,
    DEPTH_VIDEO_LIMITS,
    MultiVideoResearchResult,
    ResearchDepth,
    SourceCitation,
    VideoResearchSummary,
)


def test_research_depth_enum_values():
    assert ResearchDepth.QUICK == "quick"
    assert ResearchDepth.STANDARD == "standard"
    assert ResearchDepth.DEEP == "deep"

    assert DEPTH_VIDEO_LIMITS[ResearchDepth.QUICK] == 2
    assert DEPTH_VIDEO_LIMITS[ResearchDepth.STANDARD] == 3
    assert DEPTH_VIDEO_LIMITS[ResearchDepth.DEEP] == 5

    assert DEPTH_CITATIONS_PER_VIDEO[ResearchDepth.QUICK] == 2
    assert DEPTH_CITATIONS_PER_VIDEO[ResearchDepth.STANDARD] == 3
    assert DEPTH_CITATIONS_PER_VIDEO[ResearchDepth.DEEP] == 5


def test_research_depth_validation():
    # Valid enum parsing
    res = MultiVideoResearchResult(
        topic="AI Testing",
        depth=ResearchDepth.QUICK,
        total_videos_analyzed=2,
        videos_with_transcripts=2,
        total_evidence_chunks=4,
        sources=[],
        all_citations_ranked=[],
    )
    assert res.depth == ResearchDepth.QUICK

    # Invalid enum string should fail validation
    with pytest.raises(ValidationError):
        MultiVideoResearchResult(
            topic="AI Testing",
            depth="invalid_depth_value",  # type: ignore
            total_videos_analyzed=0,
            videos_with_transcripts=0,
            total_evidence_chunks=0,
            sources=[],
            all_citations_ranked=[],
        )
