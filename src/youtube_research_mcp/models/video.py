from typing import List, Optional
from pydantic import BaseModel, Field


class Chapter(BaseModel):
    """Video chapter timestamp and title."""

    title: str = Field(description="Chapter title")
    start_seconds: float = Field(description="Start time in seconds")
    end_seconds: Optional[float] = Field(default=None, description="End time in seconds")
    timestamp_formatted: str = Field(description="Human readable timestamp e.g. 04:15")
    url: str = Field(description="Clickable deep link URL to chapter start")


class VideoOverview(BaseModel):
    """Comprehensive video metadata and structural overview."""

    video_id: str = Field(description="11-character YouTube video ID")
    title: str = Field(description="Video title")
    channel: str = Field(description="Channel / Creator name")
    channel_id: Optional[str] = Field(default=None, description="Channel ID or handle")
    published_date: Optional[str] = Field(default=None, description="Published date string")
    duration_seconds: Optional[int] = Field(default=None, description="Video duration in seconds")
    duration_formatted: str = Field(description="Human readable duration e.g. 15m 30s")
    view_count: Optional[int] = Field(default=None, description="Total views if available")
    description: Optional[str] = Field(default=None, description="Full or truncated video description")
    tags: List[str] = Field(default_factory=list, description="Video tags/keywords")
    chapters: List[Chapter] = Field(default_factory=list, description="Timestamped chapters")
    caption_available: bool = Field(default=False, description="Whether transcripts/captions are available")
    available_languages: List[str] = Field(default_factory=list, description="Available caption language codes")
    url: str = Field(description="Canonical YouTube video URL")
    thumbnail_url: Optional[str] = Field(default=None, description="High-resolution thumbnail URL")
