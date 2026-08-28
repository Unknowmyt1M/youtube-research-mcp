import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.models.transcript import TranscriptResult


class ProviderHealth(BaseModel):
    """Real-time provider health score and performance metrics."""

    provider_name: str
    is_healthy: bool = True
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    last_failure_reason: Optional[str] = None
    circuit_open_until: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def record_success(self, latency_ms: float):
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.is_healthy = True
        self.circuit_open_until = 0.0
        # Exponential moving average for latency
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.8 * self.avg_latency_ms + 0.2 * latency_ms

    def record_failure(self, reason: str, trip_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_reason = reason
        if self.consecutive_failures >= trip_threshold:
            self.is_healthy = False
            self.circuit_open_until = time.time() + cooldown_seconds

    def is_available(self) -> bool:
        if not self.is_healthy:
            if time.time() > self.circuit_open_until:
                # Half-open test trial
                return True
            return False
        return True


class BaseSearchProvider(ABC):
    """Abstract interface for YouTube search providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> ProviderHealth:
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> List[VideoSearchResult]:
        pass


class BaseMetadataProvider(ABC):
    """Abstract interface for YouTube video metadata resolution."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> ProviderHealth:
        pass

    @abstractmethod
    async def get_video(self, video_id: str) -> Optional[VideoOverview]:
        pass


class BaseTranscriptProvider(ABC):
    """Abstract interface for YouTube transcript extraction."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> ProviderHealth:
        pass

    @abstractmethod
    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        pass
