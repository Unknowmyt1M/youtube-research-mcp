import asyncio
import logging
from typing import List, Optional

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.transcript import TranscriptResult
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.providers.base import (
    BaseMetadataProvider,
    BaseSearchProvider,
    BaseTranscriptProvider,
    ProviderHealth,
)
from youtube_research_mcp.providers.commercial import CommercialFallbackProvider
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider

logger = logging.getLogger(settings.MCP_SERVER_NAME)


class ProviderRouter:
    """Intelligent multi-tier router with failover, health tracking, and circuit breaker."""

    def __init__(self):
        self.innertube = InnerTubeProvider()
        self.ytdlp = YtDlpProvider()
        self.commercial = CommercialFallbackProvider()

        self.search_providers: List[BaseSearchProvider] = [
            self.innertube,
            self.ytdlp,
        ]
        self.metadata_providers: List[BaseMetadataProvider] = [
            self.innertube,
            self.ytdlp,
        ]
        self.transcript_providers: List[BaseTranscriptProvider] = [
            self.innertube,
            self.ytdlp,
            self.commercial,
        ]

    def get_health_report(self) -> List[ProviderHealth]:
        return [
            self.innertube.health,
            self.ytdlp.health,
            self.commercial.health,
        ]

    # -------------------------------------------------------------
    # SEARCH ROUTING
    # -------------------------------------------------------------
    async def route_search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> List[VideoSearchResult]:
        for provider in self.search_providers:
            if not provider.health.is_available():
                logger.warning(
                    f"Skipping search provider {provider.name} (circuit open)"
                )
                continue

            try:
                results = await asyncio.wait_for(
                    provider.search(
                        query=query,
                        max_results=max_results,
                        language=language,
                        published_after=published_after,
                        published_before=published_before,
                    ),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                if results:
                    return results
            except Exception as e:
                logger.warning(
                    f"Search provider {provider.name} failed: {e}. Falling back."
                )
                provider.health.record_failure(str(e))

        return []

    # -------------------------------------------------------------
    # METADATA ROUTING
    # -------------------------------------------------------------
    async def route_metadata(self, video_id: str) -> Optional[VideoOverview]:
        for provider in self.metadata_providers:
            if not provider.health.is_available():
                continue

            try:
                overview = await asyncio.wait_for(
                    provider.get_video(video_id),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                if overview:
                    return overview
            except Exception as e:
                logger.warning(
                    f"Metadata provider {provider.name} failed: {e}. Falling back."
                )
                provider.health.record_failure(str(e))

        return None

    # -------------------------------------------------------------
    # TRANSCRIPT ROUTING
    # -------------------------------------------------------------
    async def route_transcript(
        self,
        video_id: str,
        language: str = "en",
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        for provider in self.transcript_providers:
            if not provider.health.is_available():
                continue

            try:
                transcript = await asyncio.wait_for(
                    provider.get_transcript(
                        video_id=video_id,
                        language=language,
                        translate_to=translate_to,
                    ),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                if transcript and transcript.segments:
                    return transcript
            except Exception as e:
                logger.warning(
                    f"Transcript provider {provider.name} failed: {e}. Falling back."
                )
                provider.health.record_failure(str(e))

        return None


# Global singleton router
_global_router: Optional[ProviderRouter] = None


def get_router() -> ProviderRouter:
    global _global_router
    if _global_router is None:
        _global_router = ProviderRouter()
    return _global_router
