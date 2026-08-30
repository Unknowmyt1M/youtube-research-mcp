import asyncio
import logging
from typing import Any, List, Optional
import httpx

from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.models.transcript import TranscriptResult
from youtube_research_mcp.providers.base import (
    BaseMetadataProvider,
    BaseSearchProvider,
    BaseTranscriptProvider,
    CircuitState,
    ProviderCapability,
    ProviderHealthReport,
)
from youtube_research_mcp.providers.commercial import CommercialProvider
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import get_single_flight

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Adaptive capability-aware failover coordinator with async single-flight request coalescing."""

    def __init__(self):
        self.innertube = InnerTubeProvider()
        self.ytdlp = YtDlpProvider()
        self.commercial = CommercialProvider()

        self.search_providers: List[BaseSearchProvider] = [
            self.innertube,
            self.ytdlp,
        ]
        self.metadata_providers: List[BaseMetadataProvider] = [
            self.innertube,
            self.ytdlp,
        ]
        self.transcript_providers: List[BaseTranscriptProvider] = [
            self.ytdlp,  # Tier 1 for transcripts due to anti-bot client rotation
            self.innertube,
            self.commercial,
        ]
        self.flight = get_single_flight()

    def _get_adaptive_providers(
        self, providers: List[Any], capability: ProviderCapability
    ) -> List[Any]:
        """Rank executable providers adaptively by circuit health, historical success rate, and latency."""
        executable = []
        for p in providers:
            if p.health.can_execute(capability):
                executable.append(p)
            else:
                logger.info(
                    f"Provider '{p.name}' capability '{capability.value}' skipped (circuit breaker state is OPEN)."
                )
        if not executable:
            return []

        def _sort_key(provider_item):
            idx, provider = provider_item
            breaker = provider.health.breakers.get(capability)
            if not breaker:
                return (1, 0.0, 999999.0, idx)

            # State priority: CLOSED (0), HALF_OPEN (1), OPEN (2)
            state_val = 0 if breaker.state == CircuitState.CLOSED else (1 if breaker.state == CircuitState.HALF_OPEN else 2)
            # Success rate: higher is better (negate for ascending sort)
            success_rate = breaker.success_rate
            # Avg latency: lower is better
            latency = breaker.avg_latency_ms if breaker.avg_latency_ms > 0 else 500.0

            return (state_val, -success_rate, latency, idx)

        enumerated = list(enumerate(executable))
        enumerated.sort(key=_sort_key)
        return [p for _, p in enumerated]

    async def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> List[VideoSearchResult]:
        flight_key = f"search:{query}:{max_results}:{language}:{published_after}:{published_before}"

        async def _do_search():
            metrics.record_request("search")
            candidates = self._get_adaptive_providers(
                self.search_providers, ProviderCapability.SEARCH
            )
            for provider in candidates:
                try:
                    res = await provider.search(
                        query=query,
                        max_results=max_results,
                        language=language,
                        published_after=published_after,
                        published_before=published_before,
                    )
                    if res:
                        return res
                except Exception as e:
                    logger.warning(
                        f"Search provider '{provider.name}' failed: {e}. Trying next tier."
                    )
            return []

        return await self.flight.execute(flight_key, _do_search)

    async def get_video(self, video_id: str) -> Optional[VideoOverview]:
        flight_key = f"metadata:{video_id}"

        async def _do_metadata():
            metrics.record_request("metadata")
            candidates = self._get_adaptive_providers(
                self.metadata_providers, ProviderCapability.METADATA
            )
            for provider in candidates:
                try:
                    res = await provider.get_video(video_id)
                    if res:
                        return res
                except Exception as e:
                    logger.warning(
                        f"Metadata provider '{provider.name}' failed for {video_id}: {e}."
                    )
            return None

        return await self.flight.execute(flight_key, _do_metadata)

    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        fallback_language: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        flight_key = f"transcript:{video_id}:{language}:{fallback_language}:{translate_to}"

        async def _do_transcript():
            metrics.record_request("transcript")
            candidates = self._get_adaptive_providers(
                self.transcript_providers, ProviderCapability.TRANSCRIPT
            )
            for provider in candidates:
                try:
                    res = await provider.get_transcript(
                        video_id=video_id,
                        language=language,
                        fallback_language=fallback_language,
                        translate_to=translate_to,
                    )
                    if res and res.segments:
                        return res
                except Exception as e:
                    logger.warning(
                        f"Transcript provider '{provider.name}' failed for {video_id}: {e}."
                    )
            return None

        return await self.flight.execute(flight_key, _do_transcript)

    def get_health_report(self) -> List[ProviderHealthReport]:
        return [
            self.innertube.health.get_report(),
            self.ytdlp.health.get_report(),
            self.commercial.health.get_report(),
        ]

    async def close(self):
        """Close provider HTTP clients."""
        await self.innertube.close()
        await self.ytdlp.close()
        await self.commercial.close()


# Global router singleton
_router_instance: Optional[ProviderRouter] = None


def get_router() -> ProviderRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ProviderRouter()
    return _router_instance
