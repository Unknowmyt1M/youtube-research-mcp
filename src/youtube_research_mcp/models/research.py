from typing import List, Optional
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    """Accurate source citation with deep-link timestamp provenance."""

    video_id: str = Field(description="11-character video ID")
    video_title: str = Field(description="Title of video")
    channel: str = Field(description="Creator / Channel name")
    start_seconds: float = Field(description="Start time of quote/section")
    end_seconds: float = Field(description="End time of quote/section")
    time_range: str = Field(description="Formatted time range e.g. 12:42 - 14:15")
    url_with_timestamp: str = Field(description="Direct clickable YouTube link with ?t=XXs")
    quote: str = Field(description="Exact spoken excerpt from transcript")
    relevance: float = Field(description="Relevance score to research topic")


class VideoResearchSummary(BaseModel):
    """Summary of findings from an individual video in a research batch."""

    video_id: str = Field(description="11-character video ID")
    title: str = Field(description="Video title")
    channel: str = Field(description="Channel name")
    url: str = Field(description="Video URL")
    duration: Optional[str] = Field(default=None, description="Video length")
    caption_found: bool = Field(description="Whether transcript was available")
    key_citations: List[SourceCitation] = Field(default_factory=list, description="Top matching citations")


class MultiVideoResearchResult(BaseModel):
    """Complete multi-video research aggregation with cross-video evidence."""

    topic: str = Field(description="Research query topic")
    depth: str = Field(default="standard", description="Research depth: quick | standard | deep")
    total_videos_analyzed: int = Field(description="Number of candidate videos discovered")
    videos_with_transcripts: int = Field(description="Number of videos successfully transcribed")
    total_evidence_chunks: int = Field(description="Total relevant evidence chunks extracted")
    sources: List[VideoResearchSummary] = Field(default_factory=list, description="Findings per video source")
    all_citations_ranked: List[SourceCitation] = Field(
        default_factory=list, description="All citations ranked globally by relevance"
    )
