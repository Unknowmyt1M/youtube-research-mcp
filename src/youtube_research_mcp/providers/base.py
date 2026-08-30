from abc import ABC, abstractmethod
from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.models.transcript import TranscriptResult


class ProviderCapability(str, Enum):
    """Specific functional capabilities that can fail and break independently."""

    SEARCH = "search"
    METADATA = "metadata"
    TRANSCRIPT = "transcript"


class ErrorCategory(str, Enum):
    """Explicit taxonomy for internal error tracking and telemetry."""

    VIDEO_NOT_FOUND = "VIDEO_NOT_FOUND"
    VIDEO_PRIVATE = "VIDEO_PRIVATE"
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    NO_CAPTIONS = "NO_CAPTIONS"
    LANGUAGE_NOT_AVAILABLE = "LANGUAGE_NOT_AVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_NETWORK_ERROR = "PROVIDER_NETWORK_ERROR"
    PROVIDER_BLOCKED = "PROVIDER_BLOCKED"
    PROVIDER_PARSE_ERROR = "PROVIDER_PARSE_ERROR"
    PROVIDER_CIRCUIT_OPEN = "PROVIDER_CIRCUIT_OPEN"


class CircuitState(str, Enum):
    """Circuit breaker state machine."""

    CLOSED = "CLOSED"  # Healthy, normal operations
    OPEN = "OPEN"  # Tripped, requests fail fast to next tier
    HALF_OPEN = "HALF_OPEN"  # Cooldown elapsed, allowing 1 single probe request


class CapabilityCircuitBreaker:
    """Individual state machine circuit breaker for a specific provider capability."""

    def __init__(
        self,
        capability: ProviderCapability,
        fail_threshold: int = settings.CIRCUIT_BREAKER_FAIL_THRESHOLD,
        cooldown_seconds: float = settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    ):
        self.capability = capability
        self.fail_threshold = fail_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.total_requests: int = 0
        self.last_failure_time: float = 0.0
        self.last_failure_reason: Optional[str] = None
        self.probe_in_flight: bool = False
        self.total_latency_ms: float = 0.0

    def can_execute(self) -> bool:
        """Determines if a request is allowed through or should fail fast."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.cooldown_seconds:
                # Transition to HALF_OPEN to test 1 probe
                self.state = CircuitState.HALF_OPEN
                self.probe_in_flight = True
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Only allow ONE probe in flight during HALF_OPEN
            if not self.probe_in_flight:
                self.probe_in_flight = True
                return True
            return False

        return False

    def record_success(self, latency_ms: float):
        """Record successful execution and close the circuit if probe succeeded."""
        self.total_requests += 1
        self.success_count += 1
        self.total_latency_ms += latency_ms
        self.failure_count = 0
        self.probe_in_flight = False
        self.state = CircuitState.CLOSED

    def record_failure(self, reason: str):
        """Record failure and trip circuit to OPEN if threshold reached."""
        self.total_requests += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.last_failure_reason = reason
        self.probe_in_flight = False

        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.fail_threshold:
            self.state = CircuitState.OPEN

    @property
    def avg_latency_ms(self) -> float:
        return (
            self.total_latency_ms / max(1, self.success_count)
            if self.success_count > 0
            else 0.0
        )

    @property
    def success_rate(self) -> float:
        return (
            self.success_count / max(1, self.total_requests)
            if self.total_requests > 0
            else 1.0
        )


class ProviderHealthReport(BaseModel):
    """Detailed health status report for a provider and its capabilities."""

    provider_name: str
    is_healthy: bool
    capabilities: Dict[str, Dict[str, Any]]
    total_requests: int
    success_rate: float
    avg_latency_ms: float
    last_failure_reason: Optional[str] = None


class CapabilityProviderHealth:
    """Manages capability-level circuit breakers and health telemetry for a provider."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.breakers: Dict[ProviderCapability, CapabilityCircuitBreaker] = {
            ProviderCapability.SEARCH: CapabilityCircuitBreaker(ProviderCapability.SEARCH),
            ProviderCapability.METADATA: CapabilityCircuitBreaker(ProviderCapability.METADATA),
            ProviderCapability.TRANSCRIPT: CapabilityCircuitBreaker(ProviderCapability.TRANSCRIPT),
        }

    def can_execute(self, capability: ProviderCapability) -> bool:
        breaker = self.breakers.get(capability)
        return breaker.can_execute() if breaker else True

    def record_success(self, capability: ProviderCapability, latency_ms: float):
        breaker = self.breakers.get(capability)
        if breaker:
            breaker.record_success(latency_ms)

    def record_failure(self, capability: ProviderCapability, reason: str):
        breaker = self.breakers.get(capability)
        if breaker:
            breaker.record_failure(reason)

    def get_report(self) -> ProviderHealthReport:
        caps_dict = {}
        total_reqs = sum(b.total_requests for b in self.breakers.values())
        total_succ = sum(b.success_count for b in self.breakers.values())
        total_lat = sum(b.total_latency_ms for b in self.breakers.values())
        last_reason = next(
            (b.last_failure_reason for b in self.breakers.values() if b.last_failure_reason),
            None,
        )

        all_healthy = all(b.state != CircuitState.OPEN for b in self.breakers.values())

        for cap, b in self.breakers.items():
            caps_dict[cap.value] = {
                "state": b.state.value,
                "success_rate": round(b.success_rate * 100, 1),
                "total_requests": b.total_requests,
                "failure_count": b.failure_count,
                "avg_latency_ms": round(b.avg_latency_ms, 1),
                "last_failure": b.last_failure_reason,
            }

        return ProviderHealthReport(
            provider_name=self.provider_name,
            is_healthy=all_healthy,
            capabilities=caps_dict,
            total_requests=total_reqs,
            success_rate=round(total_succ / max(1, total_reqs), 3) if total_reqs > 0 else 1.0,
            avg_latency_ms=round(total_lat / max(1, total_succ), 1) if total_succ > 0 else 0.0,
            last_failure_reason=last_reason,
        )


class BaseSearchProvider(ABC):
    """Abstract interface for video search providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> CapabilityProviderHealth:
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
    """Abstract interface for video metadata providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> CapabilityProviderHealth:
        pass

    @abstractmethod
    async def get_video(self, video_id: str) -> Optional[VideoOverview]:
        pass


class BaseTranscriptProvider(ABC):
    """Abstract interface for transcript extraction providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def health(self) -> CapabilityProviderHealth:
        pass

    @abstractmethod
    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        fallback_language: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        pass
