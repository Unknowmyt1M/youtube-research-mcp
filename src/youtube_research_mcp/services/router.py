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
    """Capability-aware failover coordinator with async single-flight request coalescing."""

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
            for provider in self.search_providers:
                if not provider.health.can_execute(ProviderCapability.SEARCH):
                    continue
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
            for provider in self.metadata_providers:
                if not provider.health.can_execute(ProviderCapability.METADATA):
                    continue
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
            for provider in self.transcript_providers:
                if not provider.health.can_execute(ProviderCapability.TRANSCRIPT):
                    continue
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
