import asyncio
import logging
import time
from typing import Any, List, Optional
import httpx

from youtube_research_mcp.config import settings
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
from youtube_research_mcp.providers.youtube_transcript_api_provider import (
    YouTubeTranscriptApiProvider,
)
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import get_single_flight

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Adaptive capability-aware failover coordinator with async single-flight request coalescing."""

    def __init__(self):
        # Tier 1: Direct Free Providers
        self.yta_direct = YouTubeTranscriptApiProvider(
            proxy=None, name="youtube_transcript_api"
        )
        self.ytdlp_direct = YtDlpProvider(proxy=None, name="yt-dlp")
        self.innertube = InnerTubeProvider()

        # Aliases for backward compatibility
        self.yta = self.yta_direct
        self.ytdlp = self.ytdlp_direct

        self.direct_transcript_providers: List[BaseTranscriptProvider] = [
            self.yta_direct,
            self.ytdlp_direct,
            self.innertube,
        ]

        # Tier 2: Proxied / Residential Free Route (only activated when configured)
        self.proxy_url = settings.RESIDENTIAL_PROXY_URL or (
            settings.HTTP_PROXY if settings.YOUTUBE_PROXY_ENABLED else None
        )
        if self.proxy_url:
            self.yta_proxied = YouTubeTranscriptApiProvider(
                proxy=self.proxy_url,
                name="residential_proxy_youtube_transcript_api",
            )
            self.ytdlp_proxied = YtDlpProvider(
                proxy=self.proxy_url, name="residential_proxy_yt_dlp"
            )
            self.proxied_transcript_providers: List[BaseTranscriptProvider] = [
                self.yta_proxied,
                self.ytdlp_proxied,
            ]
        else:
            self.yta_proxied = None
            self.ytdlp_proxied = None
            self.proxied_transcript_providers: List[BaseTranscriptProvider] = []

        # Tier 3: Commercial Fallback (LAST RESORT ONLY)
        self.commercial = CommercialProvider()
        self.supadata_daily_calls: int = 0
        self.supadata_daily_date: str = ""

        # Search & Metadata providers
        self.search_providers: List[BaseSearchProvider] = [
            self.innertube,
            self.ytdlp_direct,
        ]
        self.metadata_providers: List[BaseMetadataProvider] = [
            self.innertube,
            self.ytdlp_direct,
        ]
        self.free_transcript_providers: List[BaseTranscriptProvider] = (
            self.direct_transcript_providers
        )
        self.commercial_providers: List[BaseTranscriptProvider] = [
            self.commercial,
        ]
        self.transcript_providers: List[BaseTranscriptProvider] = (
            self.direct_transcript_providers
            + self.proxied_transcript_providers
            + [self.commercial]
        )
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
            logger.warning(
                f"All providers for capability '{capability.value}' have tripped circuit breakers. Falling back to default provider order."
            )
            return providers

        def _sort_key(provider_item):
            idx, provider = provider_item
            breaker = provider.health.breakers.get(capability)
            if not breaker:
                return (1, 0.0, 999999.0, idx)

            # State priority: CLOSED (0), HALF_OPEN (1), OPEN (2)
            state_val = (
                0
                if breaker.state == CircuitState.CLOSED
                else (1 if breaker.state == CircuitState.HALF_OPEN else 2)
            )
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

            content_missing_confirmed = False
            network_error_occurred = False

            async def _try_providers(
                candidates: List[BaseTranscriptProvider],
            ) -> Optional[TranscriptResult]:
                nonlocal content_missing_confirmed, network_error_occurred
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

                        breaker = provider.health.breakers.get(
                            ProviderCapability.TRANSCRIPT
                        )
                        reason = (
                            breaker.last_failure_reason if breaker else ""
                        ) or ""

                        if any(
                            c in reason
                            for c in [
                                "NoTranscriptFound",
                                "TranscriptsDisabled",
                                "VideoUnavailable",
                                "InvalidVideoId",
                                "No captions found",
                                "TranslationLanguageNotAvailable",
                            ]
                        ):
                            content_missing_confirmed = True
                        if any(
                            n in reason
                            for n in [
                                "IpBlocked",
                                "RequestBlocked",
                                "PoTokenRequired",
                                "429",
                                "timed out",
                                "NetworkError",
                                "Connection",
                                "ConnectError",
                            ]
                        ):
                            network_error_occurred = True

                    except Exception as e:
                        network_error_occurred = True
                        logger.warning(
                            f"Transcript provider '{provider.name}' failed for {video_id}: {e}."
                        )
                return None

            # --- TIER 1: Direct Free Providers ---
            direct_candidates = self._get_adaptive_providers(
                self.direct_transcript_providers, ProviderCapability.TRANSCRIPT
            )
            direct_res = await _try_providers(direct_candidates)
            if direct_res and direct_res.segments:
                return direct_res

            # --- TIER 2: Proxied / Residential Free Route (if configured) ---
            if self.proxied_transcript_providers:
                proxied_candidates = self._get_adaptive_providers(
                    self.proxied_transcript_providers, ProviderCapability.TRANSCRIPT
                )
                proxied_res = await _try_providers(proxied_candidates)
                if proxied_res and proxied_res.segments:
                    return proxied_res

            # --- TIER 2.5: Cost Guard for Verified Missing Content ---
            if content_missing_confirmed and not network_error_occurred:
                logger.info(
                    f"Video {video_id} confirmed to have no captions by free providers. Skipping commercial fallback to protect quota."
                )
                return None

            # --- TIER 3: Supadata Commercial Fallback (LAST RESORT ONLY) ---
            curr_date = time.strftime("%Y-%m-%d")
            if self.supadata_daily_date != curr_date:
                self.supadata_daily_date = curr_date
                self.supadata_daily_calls = 0

            if (
                settings.SUPADATA_MAX_DAILY_REQUESTS is not None
                and self.supadata_daily_calls >= settings.SUPADATA_MAX_DAILY_REQUESTS
            ):
                logger.warning(
                    f"Supadata daily quota reached ({self.supadata_daily_calls}/{settings.SUPADATA_MAX_DAILY_REQUESTS}). "
                    "Skipping commercial fallback to enforce daily budget cap."
                )
                return None

            if self.commercial.health.can_execute(ProviderCapability.TRANSCRIPT):
                logger.info(
                    f"All free routes exhausted due to network/datacenter challenge for {video_id}. Attempting LAST-RESORT commercial fallback."
                )
                try:
                    res = await self.commercial.get_transcript(
                        video_id=video_id,
                        language=language,
                        fallback_language=fallback_language,
                        translate_to=translate_to,
                    )
                    if res and res.segments:
                        self.supadata_daily_calls += 1
                        return res
                except Exception as e:
                    logger.error(f"Commercial fallback failed for {video_id}: {e}.")

            return None

        return await self.flight.execute(flight_key, _do_transcript)

    def get_health_report(self) -> List[ProviderHealthReport]:
        reports = [
            self.yta_direct.health.get_report(),
            self.innertube.health.get_report(),
            self.ytdlp_direct.health.get_report(),
        ]
        if self.yta_proxied:
            reports.append(self.yta_proxied.health.get_report())
        if self.ytdlp_proxied:
            reports.append(self.ytdlp_proxied.health.get_report())
        reports.append(self.commercial.health.get_report())
        return reports

    async def close(self):
        """Close provider HTTP clients."""
        await self.yta_direct.close()
        await self.innertube.close()
        await self.ytdlp_direct.close()
        if self.yta_proxied:
            await self.yta_proxied.close()
        if self.ytdlp_proxied:
            await self.ytdlp_proxied.close()
        await self.commercial.close()


# Global router singleton
_router_instance: Optional[ProviderRouter] = None


def get_router() -> ProviderRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ProviderRouter()
    return _router_instance
