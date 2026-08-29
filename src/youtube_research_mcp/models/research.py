from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchDepth(str, Enum):
    """Strict research depth enum controlling video coverage and quote density."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


DEPTH_VIDEO_LIMITS = {
    ResearchDepth.QUICK: 2,
    ResearchDepth.STANDARD: 3,
    ResearchDepth.DEEP: 5,
}

DEPTH_CITATIONS_PER_VIDEO = {
    ResearchDepth.QUICK: 2,
    ResearchDepth.STANDARD: 3,
    ResearchDepth.DEEP: 5,
}


class SourceCitation(BaseModel):
    """Specific spoken evidence segment with deep link URL and attribution."""

    video_id: str
    video_title: str
    channel: str
    start_seconds: float
    end_seconds: float
    time_range: str
    url_with_timestamp: str
    quote: str
    relevance: float
    language: Optional[str] = "en"


class VideoResearchSummary(BaseModel):
    """Summary of research findings extracted from a single video."""

    video_id: str
    title: str
    channel: str
    url: str
    duration: Optional[str] = None
    caption_found: bool
    language: Optional[str] = "en"
    key_citations: List[SourceCitation] = Field(default_factory=list)


class ClaimEvidenceCluster(BaseModel):
    """Grouped evidence from multiple videos corroborating or discussing the same finding."""

    cluster_id: str
    topic_headline: str
    independent_sources_count: int
    consensus_score: float
    channels: List[str]
    citations: List[SourceCitation]


class MultiVideoResearchResult(BaseModel):
    """Structured research synthesis across multiple candidate YouTube videos."""

    topic: str
    depth: ResearchDepth
    total_videos_analyzed: int
    videos_with_transcripts: int
    total_evidence_chunks: int
    sources: List[VideoResearchSummary]
    evidence_clusters: List[ClaimEvidenceCluster] = Field(default_factory=list)
    all_citations_ranked: List[SourceCitation]
