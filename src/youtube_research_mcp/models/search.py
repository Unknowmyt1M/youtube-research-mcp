from typing import List, Optional
from pydantic import BaseModel, Field


class VideoSearchResult(BaseModel):
    """Structured YouTube video search result."""

    video_id: str = Field(description="11-character YouTube video ID")
    title: str = Field(description="Video title")
    channel: str = Field(description="Creator / Channel name")
    channel_id: Optional[str] = Field(default=None, description="Channel ID or handle")
    published_time: Optional[str] = Field(default=None, description="Relative or absolute upload date")
    duration: Optional[str] = Field(default=None, description="Video duration string e.g. 14:20")
    duration_seconds: Optional[int] = Field(default=None, description="Video duration in seconds")
    view_count: Optional[str] = Field(default=None, description="View count string e.g. 1.2M views")
    view_count_num: Optional[int] = Field(default=None, description="Numeric views if available")
    description_snippet: Optional[str] = Field(default=None, description="Short snippet from video description")
    url: str = Field(description="Canonical YouTube video URL")
    thumbnail: Optional[str] = Field(default=None, description="Video thumbnail URL")
    relevance_score: Optional[float] = Field(default=None, description="Relevance rank score")


class SearchResponse(BaseModel):
    """Search query response."""

    query: str = Field(description="Search term queried")
    total_results: int = Field(description="Number of results returned")
    results: List[VideoSearchResult] = Field(default_factory=list, description="Ranked video results")
