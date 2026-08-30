import json
import re
import time
from typing import Any, Dict, List, Optional
import httpx

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.models.video import Chapter, VideoOverview
from youtube_research_mcp.models.transcript import (
    TranscriptResult,
    TranscriptSegment,
    WordTiming,
)
from youtube_research_mcp.providers.base import (
    BaseMetadataProvider,
    BaseSearchProvider,
    BaseTranscriptProvider,
    CapabilityProviderHealth,
    ProviderCapability,
)
from youtube_research_mcp.utils.formatting import (
    format_duration,
    format_timestamp,
    make_timestamp_url,
    parse_timestamp,
)
from youtube_research_mcp.utils.security import canonical_video_url, extract_video_id


class InnerTubeProvider(
    BaseSearchProvider, BaseMetadataProvider, BaseTranscriptProvider
):
    """Direct InnerTube HTTP/2 client with shared connection pooling and capability health tracking."""

    SEARCH_URL = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
    PLAYER_URL = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"

    CLIENT_CONFIGS = {
        "WEB": {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20250101.01.00",
                    "hl": "en",
                    "gl": "US",
                    "utcOffsetMinutes": 0,
                }
            },
            "headers": {
                "User-Agent": settings.USER_AGENT,
                "Content-Type": "application/json",
                "X-YouTube-Client-Name": "1",
                "X-YouTube-Client-Version": "2.20250101.01.00",
            },
        },
        "ANDROID": {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.29.35",
                    "androidSdkVersion": 34,
                    "hl": "en",
                    "gl": "US",
                    "utcOffsetMinutes": 0,
                }
            },
            "headers": {
                "User-Agent": "com.google.android.youtube/19.29.35 (Linux; U; Android 14; US) gzip",
                "Content-Type": "application/json",
                "X-YouTube-Client-Name": "3",
                "X-YouTube-Client-Version": "19.29.35",
            },
        },
        "WEB_EMBEDDED": {
            "context": {
                "client": {
                    "clientName": "WEB_EMBEDDED_PLAYER",
                    "clientVersion": "1.20250101.01.00",
                    "hl": "en",
                    "gl": "US",
                    "utcOffsetMinutes": 0,
                }
            },
            "headers": {
                "User-Agent": settings.USER_AGENT,
                "Content-Type": "application/json",
                "X-YouTube-Client-Name": "56",
                "X-YouTube-Client-Version": "1.20250101.01.00",
            },
        },
        "TV_EMBEDDED": {
            "context": {
                "client": {
                    "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                    "clientVersion": "2.0",
                    "hl": "en",
                    "gl": "US",
                    "utcOffsetMinutes": 0,
                }
            },
            "headers": {
                "User-Agent": "Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version",
                "Content-Type": "application/json",
                "X-YouTube-Client-Name": "85",
                "X-YouTube-Client-Version": "2.0",
            },
        },
    }

    def __init__(self):
        self._health = CapabilityProviderHealth(provider_name="InnerTube")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "InnerTube"

    @property
    def health(self) -> CapabilityProviderHealth:
        return self._health

    async def get_client(self) -> httpx.AsyncClient:
        """Get or initialize the shared long-lived connection pool."""
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_connections=settings.POOL_MAX_CONNECTIONS,
                max_keepalive_connections=settings.POOL_MAX_KEEPALIVE,
            )
            self._client = httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT,
                http2=True,
                follow_redirects=True,
                limits=limits,
                proxy=settings.HTTP_PROXY,
            )
        return self._client

    async def close(self):
        """Close shared HTTP client connection pool on server shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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
        if not self._health.can_execute(ProviderCapability.SEARCH):
            return []

        start_t = time.perf_counter()
        cfg = self.CLIENT_CONFIGS["WEB"]
        payload = {
            "context": cfg["context"],
            "query": query,
        }

        try:
            client = await self.get_client()
            resp = await client.post(
                self.SEARCH_URL, headers=cfg["headers"], json=payload
            )
            if resp.status_code != 200:
                self._health.record_failure(
                    ProviderCapability.SEARCH, f"HTTP {resp.status_code}"
                )
                return []

            data = resp.json()
            results = self._parse_search_response(data, max_results)
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self._health.record_success(ProviderCapability.SEARCH, latency_ms)
            return results

        except Exception as e:
            self._health.record_failure(ProviderCapability.SEARCH, str(e))
            return []

    def _parse_search_response(
        self, data: Dict[str, Any], max_results: int
    ) -> List[VideoSearchResult]:
        results: List[VideoSearchResult] = []
        try:
            sections = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
        except Exception:
            return []

        for section in sections:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                if "videoRenderer" in item:
                    vr = item["videoRenderer"]
                    vid = vr.get("videoId")
                    if not vid:
                        continue

                    title = ""
                    if "title" in vr and "runs" in vr["title"]:
                        title = vr["title"]["runs"][0].get("text", "")
                    elif "title" in vr and "simpleText" in vr["title"]:
                        title = vr["title"]["simpleText"]

                    channel = ""
                    channel_id = None
                    if "ownerText" in vr and "runs" in vr["ownerText"]:
                        run = vr["ownerText"]["runs"][0]
                        channel = run.get("text", "")
                        nav = run.get("navigationEndpoint", {}).get(
                            "browseEndpoint", {}
                        )
                        channel_id = nav.get("browseId")

                    dur_str = vr.get("lengthText", {}).get("simpleText")
                    dur_sec = parse_timestamp(dur_str) if dur_str else None

                    views_str = vr.get("viewCountText", {}).get("simpleText")
                    views_num = None
                    if views_str:
                        clean_v = re.sub(r"[^\d]", "", views_str)
                        if clean_v:
                            views_num = int(clean_v)

                    snippet = ""
                    if (
                        "detailedMetadataSnippets" in vr
                        and vr["detailedMetadataSnippets"]
                    ):
                        snips = vr["detailedMetadataSnippets"][0].get(
                            "snippetText", {}
                        ).get("runs", [])
                        snippet = "".join(s.get("text", "") for s in snips)
                    elif (
                        "descriptionSnippet" in vr
                        and "runs" in vr["descriptionSnippet"]
                    ):
                        snippet = "".join(
                            s.get("text", "")
                            for s in vr["descriptionSnippet"]["runs"]
                        )

                    thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url") if thumbs else None

                    pub_str = vr.get("publishedTimeText", {}).get("simpleText")
                    if not pub_str and "publishedTimeText" in vr and "runs" in vr["publishedTimeText"]:
                        pub_str = "".join(r.get("text", "") for r in vr["publishedTimeText"]["runs"])

                    results.append(
                        VideoSearchResult(
                            video_id=vid,
                            title=title,
                            channel=channel,
                            channel_id=channel_id,
                            duration=dur_str,
                            duration_seconds=dur_sec,
                            view_count=views_str,
                            view_count_num=views_num,
                            published_time=pub_str,
                            description_snippet=snippet if snippet else None,
                            url=canonical_video_url(vid),
                            thumbnail=thumb_url,
                        )
                    )

                    if len(results) >= max_results:
                        return results

        return results

    # -------------------------------------------------------------
    # METADATA IMPLEMENTATION
    # -------------------------------------------------------------
    async def get_video(self, video_id: str) -> Optional[VideoOverview]:
        if not self._health.can_execute(ProviderCapability.METADATA):
            return None

        start_t = time.perf_counter()
        clean_id = extract_video_id(video_id)
        profiles_to_try = ["WEB", "ANDROID", "WEB_EMBEDDED"]

        try:
            client = await self.get_client()
            last_err = None

            for profile in profiles_to_try:
                cfg = self.CLIENT_CONFIGS[profile]
                payload = {
                    "context": cfg["context"],
                    "videoId": clean_id,
                }
                try:
                    resp = await client.post(
                        self.PLAYER_URL, headers=cfg["headers"], json=payload
                    )
                    if resp.status_code != 200:
                        last_err = f"HTTP {resp.status_code} on profile {profile}"
                        continue

                    data = resp.json()
                    playability = data.get("playabilityStatus", {}).get("status")
                    if playability == "ERROR":
                        last_err = f"Playability ERROR: {data.get('playabilityStatus', {}).get('reason')}"
                        continue

                    # Allow metadata extraction when valid videoDetails is present
                    details = data.get("videoDetails", {})
                    if not details or not details.get("title"):
                        last_err = f"Missing videoDetails on profile {profile} (status={playability})"
                        continue

                    overview = self._parse_player_metadata(data, clean_id)
                    if not overview:
                        last_err = "Malformed player metadata structure"
                        continue

                    latency_ms = (time.perf_counter() - start_t) * 1000.0
                    self._health.record_success(ProviderCapability.METADATA, latency_ms)
                    return overview
                except Exception as ex:
                    last_err = str(ex)
                    continue

            self._health.record_failure(
                ProviderCapability.METADATA, last_err or "All InnerTube metadata profiles failed"
            )
            return None

        except Exception as e:
            self._health.record_failure(ProviderCapability.METADATA, str(e))
            return None

    def _parse_player_metadata(
        self, data: Dict[str, Any], video_id: str
    ) -> Optional[VideoOverview]:
        details = data.get("videoDetails", {})
        if not details or "title" not in details:
            return None

        title = details.get("title", "Untitled")
        channel = details.get("author", "Unknown")
        channel_id = details.get("channelId")
        duration_sec = (
            int(details.get("lengthSeconds"))
            if details.get("lengthSeconds")
            else None
        )
        description = details.get("shortDescription", "")
        view_count = (
            int(details.get("viewCount")) if details.get("viewCount") else None
        )
        tags = details.get("keywords", [])

        caption_tracks = (
            data.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        caption_avail = len(caption_tracks) > 0
        langs = [
            t.get("languageCode")
            for t in caption_tracks
            if t.get("languageCode")
        ]

        chapters = self._extract_chapters(description, video_id, duration_sec)
        thumbs = details.get("thumbnail", {}).get("thumbnails", [])
        thumb_url = thumbs[-1].get("url") if thumbs else None

        microformat = data.get("microformat", {}).get("playerMicroformatRenderer", {})
        pub_date = microformat.get("publishDate") or microformat.get("uploadDate")

        return VideoOverview(
            video_id=video_id,
            title=title,
            channel=channel,
            channel_id=channel_id,
            duration_seconds=duration_sec,
            duration_formatted=format_duration(duration_sec),
            view_count=view_count,
            published_date=pub_date,
            description=description,
            tags=tags,
            chapters=chapters,
            caption_available=caption_avail,
            available_languages=langs,
            url=canonical_video_url(video_id),
            thumbnail_url=thumb_url,
        )

    def _extract_chapters(
        self, description: str, video_id: str, total_duration: Optional[int]
    ) -> List[Chapter]:
        chapters: List[Chapter] = []
        if not description:
            return chapters

        lines = description.split("\n")
        pattern = re.compile(
            r"(?:^|\s)(?:\[|\()?((\d{1,2}:)?\d{1,2}:\d{2})(?:\]|\))?\s+[-–—]?\s*(.+)$"
        )

        for line in lines:
            match = pattern.search(line.strip())
            if match:
                time_str = match.group(1)
                title_str = match.group(3).strip(" -–—[]()")
                start_sec = parse_timestamp(time_str)
                chapters.append(
                    Chapter(
                        title=title_str,
                        start_seconds=start_sec,
                        timestamp_formatted=format_timestamp(start_sec),
                        url=make_timestamp_url(video_id, start_sec),
                    )
                )

        chapters.sort(key=lambda c: c.start_seconds)
        for i in range(len(chapters)):
            if i + 1 < len(chapters):
                chapters[i].end_seconds = chapters[i + 1].start_seconds
            elif total_duration:
                chapters[i].end_seconds = float(total_duration)

        return chapters

    # -------------------------------------------------------------
    # TRANSCRIPT IMPLEMENTATION
    # -------------------------------------------------------------
    async def get_transcript(
        self,
        video_id: str,
        language: str = "en",
        fallback_language: Optional[str] = None,
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        if not self._health.can_execute(ProviderCapability.TRANSCRIPT):
            return None

        start_t = time.perf_counter()
        clean_id = extract_video_id(video_id)
        profiles_to_try = ["WEB", "ANDROID", "WEB_EMBEDDED"]

        try:
            client = await self.get_client()
            tracks = []
            last_err = None

            for profile in profiles_to_try:
                cfg = self.CLIENT_CONFIGS[profile]
                payload = {
                    "context": cfg["context"],
                    "videoId": clean_id,
                }
                try:
                    resp = await client.post(
                        self.PLAYER_URL, headers=cfg["headers"], json=payload
                    )
                    if resp.status_code != 200:
                        last_err = f"HTTP {resp.status_code} on {profile}"
                        continue

                    player_data = resp.json()
                    tracks = (
                        player_data.get("captions", {})
                        .get("playerCaptionsTracklistRenderer", {})
                        .get("captionTracks", [])
                    )
                    if tracks:
                        break
                except Exception as ex:
                    last_err = str(ex)
                    continue

            if not tracks:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT, last_err or "No caption tracks in InnerTube"
                )
                return None

            # Find matching track
            matched_track = next(
                (t for t in tracks if t.get("languageCode") == language),
                None,
            )
            fallback_used = False

            if not matched_track:
                # Check prefix (e.g. en-US for en)
                matched_track = next(
                    (
                        t
                        for t in tracks
                        if t.get("languageCode", "").startswith(language)
                    ),
                    None,
                )

            if not matched_track and fallback_language:
                matched_track = next(
                    (
                        t
                        for t in tracks
                        if t.get("languageCode") == fallback_language
                        or t.get("languageCode", "").startswith(fallback_language)
                    ),
                    None,
                )
                if matched_track:
                    fallback_used = True

            if not matched_track:
                # Requested language not available and no fallback matched
                return None

            base_url = matched_track.get("baseUrl")
            if not base_url:
                return None

            is_generated = matched_track.get("kind") == "asr"
            actual_lang = matched_track.get("languageCode", language)

            timedtext_url = base_url + "&fmt=json3"
            if translate_to:
                timedtext_url += f"&tlang={translate_to}"
                actual_lang = translate_to

            tt_resp = await client.get(timedtext_url)
            if tt_resp.status_code != 200:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT, f"Timedtext HTTP {tt_resp.status_code}"
                )
                return None

            data = tt_resp.json()
            segments = self._parse_json3_timedtext(data, clean_id)
            if not segments:
                return None

            full_text = " ".join(s.text for s in segments)
            dur = segments[-1].end if segments else 0.0

            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self._health.record_success(ProviderCapability.TRANSCRIPT, latency_ms)

            return TranscriptResult(
                video_id=clean_id,
                language=actual_lang,
                requested_language=language,
                actual_language=actual_lang,
                fallback_used=fallback_used,
                fallback_language=fallback_language if fallback_used else None,
                is_generated=is_generated,
                is_translated=bool(translate_to),
                total_segments=len(segments),
                total_words=len(full_text.split()),
                duration_seconds=dur,
                segments=segments,
                full_text=full_text,
            )

        except Exception as e:
            self._health.record_failure(ProviderCapability.TRANSCRIPT, str(e))
            return None

    def _parse_json3_timedtext(
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

            word_timings: List[WordTiming] = []
            text_parts: List[str] = []

            for seg in ev.get("segs", []):
                utf8 = seg.get("utf8", "")
                text_parts.append(utf8)
                t_offset = seg.get("tOffsetMs", 0)
                w_start = round((start_ms + t_offset) / 1000.0, 3)
                word_timings.append(
                    WordTiming(
                        word=utf8.strip(),
                        start=w_start,
                        end=round(w_start + 0.3, 3),
                    )
                )

            full_seg_text = "".join(text_parts).strip()
            if full_seg_text and full_seg_text != "\n":
                segments.append(
                    TranscriptSegment(
                        start=start_sec,
                        duration=dur_sec,
                        end=end_sec,
                        text=full_seg_text,
                        timestamp_formatted=format_timestamp(start_sec),
                        url=make_timestamp_url(video_id, start_sec),
                        words=word_timings if word_timings else None,
                    )
                )
                if len(segments) >= settings.MAX_TRANSCRIPT_SEGMENTS:
                    break

        return segments
