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
    ProviderHealth,
)
from youtube_research_mcp.utils.formatting import (
    format_timestamp,
    make_timestamp_url,
)
from youtube_research_mcp.utils.security import extract_video_id


class CommercialFallbackProvider(BaseTranscriptProvider):
    """Optional commercial API fallback provider (Tier 3)."""

    def __init__(self):
        self._health = ProviderHealth(provider_name="CommercialFallback")

    @property
    def name(self) -> str:
        return "CommercialFallback"

    @property
    def health(self) -> ProviderHealth:
        return self._health

    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        clean_id = extract_video_id(video_id)
        start_t = time.perf_counter()

        # 1. Supadata fallback if key is present
        if settings.SUPADATA_API_KEY:
            res = await self._fetch_supadata(clean_id, language)
            if res:
                self._health.record_success((time.perf_counter() - start_t) * 1000.0)
                return res

        # 2. TranscriptAPI.com fallback if key is present
        if settings.TRANSCRIPT_API_KEY:
            res = await self._fetch_transcriptapi(clean_id, language)
            if res:
                self._health.record_success((time.perf_counter() - start_t) * 1000.0)
                return res

        return None

    async def _fetch_supadata(
        self, video_id: str, language: str
    ) -> Optional[TranscriptResult]:
        url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={video_id}&lang={language}"
        headers = {"x-api-key": settings.SUPADATA_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_segments = data.get("content", [])
                    segments: List[TranscriptSegment] = []
                    for seg in raw_segments:
                        s_sec = seg.get("offset", 0.0) / 1000.0
                        d_sec = seg.get("duration", 0.0) / 1000.0
                        text = seg.get("text", "").strip()
                        if text:
                            segments.append(
                                TranscriptSegment(
                                    start=s_sec,
                                    duration=d_sec,
                                    end=s_sec + d_sec,
                                    text=text,
                                    timestamp_formatted=format_timestamp(s_sec),
                                    url=make_timestamp_url(video_id, s_sec),
                                )
                            )
                    if segments:
                        full_text = " ".join(s.text for s in segments)
                        return TranscriptResult(
                            video_id=video_id,
                            language=language,
                            is_generated=False,
                            is_translated=False,
                            total_segments=len(segments),
                            total_words=len(full_text.split()),
                            duration_seconds=segments[-1].end if segments else 0.0,
                            segments=segments,
                            full_text=full_text,
                        )
        except Exception:
            pass
        return None

    async def _fetch_transcriptapi(
        self, video_id: str, language: str
    ) -> Optional[TranscriptResult]:
        url = f"https://transcriptapi.com/api/v2/youtube/transcript?video_url={video_id}&format=json&include_timestamp=true"
        headers = {
            "Authorization": f"Bearer {settings.TRANSCRIPT_API_KEY}",
            "User-Agent": "YouTubeResearchMCP/1.0",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    raw_segments = resp.json()
                    segments: List[TranscriptSegment] = []
                    for seg in raw_segments:
                        s_sec = float(seg.get("start", 0.0))
                        d_sec = float(seg.get("duration", 0.0))
                        text = seg.get("text", "").strip()
                        if text:
                            segments.append(
                                TranscriptSegment(
                                    start=s_sec,
                                    duration=d_sec,
                                    end=s_sec + d_sec,
                                    text=text,
                                    timestamp_formatted=format_timestamp(s_sec),
                                    url=make_timestamp_url(video_id, s_sec),
                                )
                            )
                    if segments:
                        full_text = " ".join(s.text for s in segments)
                        return TranscriptResult(
                            video_id=video_id,
                            language=language,
                            is_generated=False,
                            is_translated=False,
                            total_segments=len(segments),
                            total_words=len(full_text.split()),
                            duration_seconds=segments[-1].end if segments else 0.0,
                            segments=segments,
                            full_text=full_text,
                        )
        except Exception:
            pass
        return None
