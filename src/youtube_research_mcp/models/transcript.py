from typing import List, Optional, Union
from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    """High-precision word-level timestamp."""

    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    """Single caption subtitle event."""

    start: float
    duration: float
    end: float
    text: str
    timestamp_formatted: str
    url: str
    words: Optional[List[WordTiming]] = None


class TranscriptChunk(BaseModel):
    """Semantically coherent chunk merged for hybrid vector/lexical retrieval."""

    chunk_id: Union[int, str]
    video_id: str
    start_seconds: float
    end_seconds: float
    start_formatted: Optional[str] = None
    end_formatted: Optional[str] = None
    time_range: str
    text: str
    word_count: int
    url: str
    chapter_title: Optional[str] = None


class TranscriptResult(BaseModel):
    """Full transcript retrieval result with explicit language metadata."""

    video_id: str
    language: str
    requested_language: str
    actual_language: str
    fallback_used: bool = False
    fallback_language: Optional[str] = None
    is_generated: bool
    is_translated: bool
    total_segments: int
    total_words: int
    duration_seconds: float
    segments: List[TranscriptSegment]
    full_text: str
    provider: Optional[str] = Field(
        default=None,
        description="Originating provider provenance (e.g. 'youtube_transcript_api', 'yt_dlp', 'innertube', 'residential_proxy_youtube_transcript_api', 'supadata', 'cache')",
    )


class TranscriptSearchMatch(BaseModel):
    """Result of hybrid search query within a long video's transcript."""

    chunk_id: Union[int, str]
    video_id: str
    time_range: str
    start_seconds: float
    end_seconds: float
    relevance_score: float
    text: str
    url: str
    chapter_title: Optional[str] = None
    language: Optional[str] = "en"
