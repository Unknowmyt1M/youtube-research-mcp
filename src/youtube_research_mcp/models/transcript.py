from typing import List, Optional
from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    """Word-level timing offset."""

    word: str = Field(description="Individual word or subword")
    start: float = Field(description="Absolute start time in seconds")


class TranscriptSegment(BaseModel):
    """Raw subtitle / caption segment with exact timestamp boundaries."""

    start: float = Field(description="Segment start time in seconds")
    duration: float = Field(description="Segment duration in seconds")
    end: float = Field(description="Segment end time in seconds")
    text: str = Field(description="Transcribed spoken text")
    timestamp_formatted: str = Field(description="Human readable timecode e.g. 01:24")
    url: str = Field(description="Deep link URL starting at segment")
    words: Optional[List[WordTiming]] = Field(default=None, description="Optional word-level timestamps")


class TranscriptChunk(BaseModel):
    """Timestamp-aware semantic chunk grouped for LLM consumption and vector indexing."""

    chunk_id: str = Field(description="Unique chunk identifier e.g. vid_c001")
    video_id: str = Field(description="11-character video ID")
    start_seconds: float = Field(description="Start time in seconds")
    end_seconds: float = Field(description="End time in seconds")
    start_formatted: str = Field(description="Human readable start time e.g. 04:12")
    end_formatted: str = Field(description="Human readable end time e.g. 05:45")
    time_range: str = Field(description="Formatted range e.g. 04:12 - 05:45")
    text: str = Field(description="Combined coherent chunk text")
    url: str = Field(description="Clickable deep link to chunk start")
    chapter_title: Optional[str] = Field(default=None, description="Enclosing chapter title if available")
    word_count: int = Field(description="Total word count of chunk")


class TranscriptResult(BaseModel):
    """Full transcript retrieval response."""

    video_id: str = Field(description="11-character YouTube video ID")
    language: str = Field(description="Language code of transcript")
    is_generated: bool = Field(default=False, description="True if automatic speech recognition (ASR)")
    is_translated: bool = Field(default=False, description="True if translated on-the-fly")
    total_segments: int = Field(description="Number of raw subtitle segments")
    total_words: int = Field(description="Total word count")
    duration_seconds: Optional[float] = Field(default=None, description="Total spoken duration covered")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Timestamped segments")
    full_text: str = Field(description="Clean, unpunctuated or punctuated continuous transcript")


class TranscriptSearchMatch(BaseModel):
    """Search match within a single video's transcript."""

    chunk_id: str = Field(description="Matched chunk ID")
    video_id: str = Field(description="Video ID")
    time_range: str = Field(description="Timecode range e.g. 14:02 - 15:30")
    start_seconds: float = Field(description="Start timestamp in seconds")
    end_seconds: float = Field(description="End timestamp in seconds")
    relevance_score: float = Field(description="Hybrid relevance score (0.0 to 1.0)")
    text: str = Field(description="Relevant quote / transcript text")
    url: str = Field(description="Direct video URL at timestamp")
    chapter_title: Optional[str] = Field(default=None, description="Chapter context")
