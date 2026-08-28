import asyncio
import time
from typing import Any, Dict, List, Optional
import httpx
import yt_dlp

from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.video import Chapter, VideoOverview
from youtube_research_mcp.models.transcript import (
    TranscriptResult,
    TranscriptSegment,
)
from youtube_research_mcp.providers.base import (
    BaseMetadataProvider,
    BaseSearchProvider,
    BaseTranscriptProvider,
    ProviderHealth,
)
from youtube_research_mcp.utils.formatting import (
    format_duration,
    format_timestamp,
    make_timestamp_url,
    parse_timestamp,
)
from youtube_research_mcp.utils.security import canonical_video_url, extract_video_id


class YtDlpProvider(
    BaseSearchProvider, BaseMetadataProvider, BaseTranscriptProvider
):
    """In-Process yt-dlp provider with robust Android/iOS/TV player client rotation to bypass bot checks."""

    def __init__(self):
        self._health = ProviderHealth(provider_name="yt-dlp")

    @property
    def name(self) -> str:
        return "yt-dlp"

    @property
    def health(self) -> ProviderHealth:
        return self._health

    def _get_base_opts(self) -> Dict[str, Any]:
        """Base yt-dlp options configured to bypass YouTube bot detection without cookies."""
        return {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "tv_embedded", "mweb"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }

    # -------------------------------------------------------------
    # SEARCH IMPLEMENTATION
    # -------------------------------------------------------------
    async def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> List[VideoSearchResult]:
        start_t = time.perf_counter()

        def _run_search():
            opts = self._get_base_opts()
            opts["extract_flat"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

        try:
            data = await asyncio.to_thread(_run_search)
            results: List[VideoSearchResult] = []
            for entry in data.get("entries", []):
                vid = entry.get("id")
                if not vid:
                    continue
                dur_sec = entry.get("duration")
                dur_str = format_timestamp(dur_sec) if dur_sec else None

                results.append(
                    VideoSearchResult(
                        video_id=vid,
                        title=entry.get("title", "Untitled"),
                        channel=entry.get("channel") or entry.get("uploader", "Unknown"),
                        channel_id=entry.get("channel_id"),
                        duration=dur_str,
                        duration_seconds=int(dur_sec) if dur_sec else None,
                        view_count=str(entry.get("view_count", "")) if entry.get("view_count") else None,
                        view_count_num=entry.get("view_count"),
                        description_snippet=entry.get("description", "")[:200] if entry.get("description") else None,
                        url=canonical_video_url(vid),
                        thumbnail=entry.get("thumbnail"),
                    )
                )

            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self._health.record_success(latency_ms)
            return results

        except Exception as e:
            self._health.record_failure(str(e))
            return []

    # -------------------------------------------------------------
    # METADATA IMPLEMENTATION
    # -------------------------------------------------------------
    async def get_video(self, video_id: str) -> Optional[VideoOverview]:
        start_t = time.perf_counter()
        clean_id = extract_video_id(video_id)

        def _run_metadata():
            opts = self._get_base_opts()
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(
                    canonical_video_url(clean_id), download=False
                )

        try:
            info = await asyncio.to_thread(_run_metadata)
            if not info:
                return None

            dur_sec = info.get("duration")
            chapters_raw = info.get("chapters", [])
            chapters: List[Chapter] = []
            if chapters_raw:
                for ch in chapters_raw:
                    s_sec = ch.get("start_time", 0.0)
                    e_sec = ch.get("end_time")
                    chapters.append(
                        Chapter(
                            title=ch.get("title", "Chapter"),
                            start_seconds=s_sec,
                            end_seconds=e_sec,
                            timestamp_formatted=format_timestamp(s_sec),
                            url=make_timestamp_url(clean_id, s_sec),
                        )
                    )

            subtitles = info.get("subtitles", {})
            auto_subs = info.get("automatic_captions", {})
            langs = list(set(list(subtitles.keys()) + list(auto_subs.keys())))

            overview = VideoOverview(
                video_id=clean_id,
                title=info.get("title", "Untitled"),
                channel=info.get("channel") or info.get("uploader", "Unknown"),
                channel_id=info.get("channel_id"),
                published_date=info.get("upload_date"),
                duration_seconds=int(dur_sec) if dur_sec else None,
                duration_formatted=format_duration(dur_sec),
                view_count=info.get("view_count"),
                description=info.get("description"),
                tags=info.get("tags", []),
                chapters=chapters,
                caption_available=len(langs) > 0,
                available_languages=langs,
                url=canonical_video_url(clean_id),
                thumbnail_url=info.get("thumbnail"),
            )

            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self._health.record_success(latency_ms)
            return overview

        except Exception as e:
            self._health.record_failure(str(e))
            return None

    # -------------------------------------------------------------
    # TRANSCRIPT IMPLEMENTATION
    # -------------------------------------------------------------
    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        start_t = time.perf_counter()
        clean_id = extract_video_id(video_id)

        def _run_transcript_extract():
            opts = self._get_base_opts()
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = True
            opts["subtitleslangs"] = [language, "en", "en-orig", ".*"]
            opts["subtitlesformat"] = "json3"
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(
                    canonical_video_url(clean_id), download=False
                )

        try:
            info = await asyncio.to_thread(_run_transcript_extract)
            if not info:
                return None

            subs = info.get("subtitles", {})
            auto_subs = info.get("automatic_captions", {})

            track_url = None
            is_gen = False
            matched_lang = language

            # Search in manual subtitles then auto captions
            candidates = [language, f"{language}-orig", "en", "en-orig", "en-US", "en-GB"]
            
            # 1. Manual captions check
            for cand in candidates:
                if cand in subs:
                    entries = subs[cand]
                    track_url = next(
                        (e["url"] for e in entries if e.get("ext") == "json3"),
                        entries[0]["url"] if entries else None,
                    )
                    if track_url:
                        matched_lang = cand
                        break

            # 2. Auto captions check
            if not track_url:
                for cand in candidates:
                    if cand in auto_subs:
                        entries = auto_subs[cand]
                        track_url = next(
                            (e["url"] for e in entries if e.get("ext") == "json3"),
                            entries[0]["url"] if entries else None,
                        )
                        if track_url:
                            is_gen = True
                            matched_lang = cand
                            break

            # 3. Any available caption track
            if not track_url:
                all_available = {**subs, **auto_subs}
                if all_available:
                    first_lang = next(iter(all_available))
                    entries = all_available[first_lang]
                    track_url = next(
                        (e["url"] for e in entries if e.get("ext") == "json3"),
                        entries[0]["url"] if entries else None,
                    )
                    matched_lang = first_lang
                    is_gen = first_lang in auto_subs

            if not track_url:
                self._health.record_failure("No subtitle tracks found in yt-dlp info")
                return None

            # Add format json3 parameter if missing
            if "fmt=json3" not in track_url:
                track_url += "&fmt=json3"

            # Translation parameter if requested
            if translate_to and f"tlang={translate_to}" not in track_url:
                track_url += f"&tlang={translate_to}"
                matched_lang = translate_to

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(track_url)
                if res.status_code == 200:
                    data = res.json()
                    segments = self._parse_json3(data, clean_id)
                    if segments:
                        full_text = " ".join(s.text for s in segments)
                        dur = segments[-1].end if segments else 0.0
                        latency_ms = (time.perf_counter() - start_t) * 1000.0
                        self._health.record_success(latency_ms)

                        return TranscriptResult(
                            video_id=clean_id,
                            language=matched_lang,
                            is_generated=is_gen,
                            is_translated=bool(translate_to),
                            total_segments=len(segments),
                            total_words=len(full_text.split()),
                            duration_seconds=dur,
                            segments=segments,
                            full_text=full_text,
                        )

        except Exception as e:
            self._health.record_failure(str(e))

        return None

    def _parse_json3(
        self, data: Dict[str, Any], video_id: str
    ) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []
        events = data.get("events", [])
        for ev in events:
            if "segs" not in ev:
                continue

            start_ms = ev.get("tStartMs", 0)
            dur_ms = ev.get("dDurationMs", 0)
            start_sec = round(start_ms / 1000.0, 3)
            dur_sec = round(dur_ms / 1000.0, 3)
            end_sec = round((start_ms + dur_ms) / 1000.0, 3)

            text = "".join(s.get("utf8", "") for s in ev.get("segs", [])).strip()
            if text and text != "\n":
                segments.append(
                    TranscriptSegment(
                        start=start_sec,
                        duration=dur_sec,
                        end=end_sec,
                        text=text,
                        timestamp_formatted=format_timestamp(start_sec),
                        url=make_timestamp_url(video_id, start_sec),
                    )
                )

        return segments
