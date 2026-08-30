import time
from typing import Any, Dict, List, Optional
import httpx

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import (
    TranscriptResult,
    TranscriptSegment,
)
from youtube_research_mcp.providers.base import (
    BaseTranscriptProvider,
    CapabilityProviderHealth,
    ProviderCapability,
)
from youtube_research_mcp.utils.formatting import format_timestamp, make_timestamp_url
from youtube_research_mcp.utils.security import extract_video_id


class CommercialProvider(BaseTranscriptProvider):
    """Optional commercial API provider (Tier 3 fallback)."""

    def __init__(self):
        self._health = CapabilityProviderHealth(provider_name="CommercialFallback")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "CommercialFallback"

    @property
    def health(self) -> CapabilityProviderHealth:
        return self._health

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        fallback_language: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        if not settings.SUPADATA_API_KEY and not settings.TRANSCRIPT_API_KEY:
            return None

        if not self._health.can_execute(ProviderCapability.TRANSCRIPT):
            return None

        start_t = time.perf_counter()
        clean_id = extract_video_id(video_id)

        try:
            client = await self.get_client()
            if settings.SUPADATA_API_KEY:
                headers = {"x-api-key": settings.SUPADATA_API_KEY}
                
                # Try primary language first
                query_url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={clean_id}&lang={language}&text=false"
                if translate_to:
                    query_url += f"&translate={translate_to}"

                res = await client.get(query_url, headers=headers)
                actual_lang = translate_to if translate_to else language
                fallback_used = False

                # If primary language failed and fallback is specified, try fallback
                if res.status_code != 200 and fallback_language and fallback_language != language:
                    fb_url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={clean_id}&lang={fallback_language}&text=false"
                    if translate_to:
                        fb_url += f"&translate={translate_to}"
                    res_fb = await client.get(fb_url, headers=headers)
                    if res_fb.status_code == 200:
                        res = res_fb
                        actual_lang = translate_to if translate_to else fallback_language
                        fallback_used = True

                if res.status_code == 200:
                    data = res.json()
                    actual_lang = translate_to or data.get("lang") or actual_lang
                    content = data.get("content", [])
                    segments = []
                    for item in content:
                        raw_offset = item.get("offset", 0.0)
                        raw_dur = item.get("duration", 0.0)
                        # Supadata provides offset and duration in milliseconds
                        s_sec = float(raw_offset) / 1000.0 if raw_offset is not None else 0.0
                        dur = float(raw_dur) / 1000.0 if raw_dur is not None else 0.0
                        segments.append(
                            TranscriptSegment(
                                start=s_sec,
                                duration=dur,
                                end=s_sec + dur,
                                text=item.get("text", "").strip(),
                                timestamp_formatted=format_timestamp(s_sec),
                                url=make_timestamp_url(clean_id, s_sec),
                            )
                        )
                        if len(segments) >= settings.MAX_TRANSCRIPT_SEGMENTS:
                            break

                    if segments:
                        full_text = " ".join(s.text for s in segments)
                        dur_total = segments[-1].end if segments else 0.0
                        latency_ms = (time.perf_counter() - start_t) * 1000.0
                        self._health.record_success(ProviderCapability.TRANSCRIPT, latency_ms)

                        return TranscriptResult(
                            video_id=clean_id,
                            language=actual_lang,
                            requested_language=language,
                            actual_language=actual_lang,
                            fallback_used=fallback_used,
                            fallback_language=fallback_language if fallback_used else None,
                            is_generated=False,
                            is_translated=bool(translate_to),
                            total_segments=len(segments),
                            total_words=len(full_text.split()),
                            duration_seconds=dur_total,
                            segments=segments,
                            full_text=full_text,
                        )

        except Exception as e:
            self._health.record_failure(ProviderCapability.TRANSCRIPT, str(e))

        return None
