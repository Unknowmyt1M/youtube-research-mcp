import asyncio
import logging
import time
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    NotTranslatable,
    PoTokenRequired,
    RequestBlocked,
    TranslationLanguageNotAvailable,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeDataUnparsable,
    YouTubeRequestFailed,
)

from youtube_research_mcp.models.transcript import (
    TranscriptResult,
    TranscriptSegment,
)
from youtube_research_mcp.providers.base import (
    BaseTranscriptProvider,
    CapabilityProviderHealth,
    ErrorCategory,
    ProviderCapability,
)
from youtube_research_mcp.utils.formatting import format_timestamp, make_timestamp_url
from youtube_research_mcp.utils.security import extract_video_id

logger = logging.getLogger(__name__)


class YouTubeTranscriptApiProvider(BaseTranscriptProvider):
    """Direct timedtext & transcript extraction provider powered by youtube-transcript-api.
    
    Provides sub-second, PO-tokenless caption extraction across manual and auto-generated
    caption tracks with multi-language fallback and translation support.
    """

    def __init__(self):
        self._health = CapabilityProviderHealth(provider_name="YouTubeTranscriptApi")
        import requests
        from youtube_research_mcp.config import settings
        session = requests.Session()
        proxies = {}
        if settings.HTTP_PROXY:
            proxies["http"] = settings.HTTP_PROXY
        if settings.HTTPS_PROXY:
            proxies["https"] = settings.HTTPS_PROXY
        if proxies:
            session.proxies.update(proxies)
        self._api = YouTubeTranscriptApi(http_client=session)

    @property
    def name(self) -> str:
        return "YouTubeTranscriptApi"

    @property
    def health(self) -> CapabilityProviderHealth:
        return self._health

    async def close(self):
        pass

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

        def _fetch_sync():
            # 1. List available transcripts
            transcript_list = self._api.list(clean_id)
            
            lang_code = language.lower()
            lang_base = lang_code.split("-")[0]
            fb_code = fallback_language.lower() if fallback_language else None
            fb_base = fb_code.split("-")[0] if fb_code else None

            # All available transcripts
            all_transcripts = list(transcript_list)
            if not all_transcripts:
                return None, None, False, False

            # Separate into manual and generated
            manual_tracks = [t for t in all_transcripts if not t.is_generated]
            generated_tracks = [t for t in all_transcripts if t.is_generated]

            candidates = []

            # 1. Exact requested language: manual first, then generated
            for t in manual_tracks:
                c = t.language_code.lower()
                if c == lang_code or c.startswith(f"{lang_base}-") or lang_code.startswith(f"{c}-"):
                    candidates.append((t, False))
            for t in generated_tracks:
                c = t.language_code.lower()
                if c == lang_code or c.startswith(f"{lang_base}-") or lang_code.startswith(f"{c}-"):
                    candidates.append((t, False))

            # 2. Fallback language (if requested and different)
            if fb_code and fb_code != lang_code:
                for t in manual_tracks:
                    c = t.language_code.lower()
                    if c == fb_code or c.startswith(f"{fb_base}-") or fb_code.startswith(f"{c}-"):
                        candidates.append((t, True))
                for t in generated_tracks:
                    c = t.language_code.lower()
                    if c == fb_code or c.startswith(f"{fb_base}-") or fb_code.startswith(f"{c}-"):
                        candidates.append((t, True))

            # 3. If translate_to is requested, include any remaining translatable track
            if translate_to:
                for t in all_transcripts:
                    if t not in [c[0] for c in candidates] and t.is_translatable:
                        candidates.append((t, fb_code is not None))

            # 4. If fallback_language is provided and no candidates matched, try all remaining tracks
            if fallback_language and not candidates:
                for t in all_transcripts:
                    candidates.append((t, True))

            # Deduplicate preserving order
            unique_candidates = []
            seen = set()
            for t, is_fb in candidates:
                key = (t.language_code, t.is_generated)
                if key not in seen:
                    seen.add(key)
                    unique_candidates.append((t, is_fb))

            if not unique_candidates:
                return None, None, False, False

            last_error = None
            for cand_t, is_fb in unique_candidates:
                target_t = cand_t
                is_trans = False
                if translate_to:
                    if target_t.is_translatable:
                        try:
                            target_t = target_t.translate(translate_to)
                            is_trans = True
                        except Exception as tr_e:
                            logger.debug(f"Failed to translate transcript {cand_t.language_code} to {translate_to}: {tr_e}")
                            continue
                    else:
                        continue

                try:
                    fetched = target_t.fetch()
                    if fetched:
                        return target_t, fetched, is_fb, is_trans
                except Exception as fetch_e:
                    last_error = fetch_e
                    logger.debug(f"Failed to fetch candidate transcript {target_t.language_code}: {fetch_e}")

            if last_error:
                raise last_error
            return None, None, False, False

        try:
            matched_tr, fetched_data, fallback_used, is_translated = await asyncio.to_thread(_fetch_sync)
            
            if not matched_tr or not fetched_data:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT,
                    "No captions found in requested language",
                )
                return None

            snippets = fetched_data.snippets if hasattr(fetched_data, "snippets") else fetched_data
            if not snippets:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT,
                    "Empty transcript snippets returned",
                )
                return None

            # Map to Nexora TranscriptSegment models
            segments = []
            for snip in snippets:
                # Handle both FetchedTranscriptSnippet dataclass and raw dict
                s_text = snip.text if hasattr(snip, "text") else snip.get("text", "")
                s_start = float(snip.start if hasattr(snip, "start") else snip.get("start", 0.0))
                s_dur = float(snip.duration if hasattr(snip, "duration") else snip.get("duration", 0.0))
                s_end = s_start + s_dur

                segments.append(
                    TranscriptSegment(
                        start=s_start,
                        duration=s_dur,
                        end=s_end,
                        text=s_text.strip(),
                        timestamp_formatted=format_timestamp(s_start),
                        url=make_timestamp_url(clean_id, s_start),
                    )
                )

            full_text = " ".join(s.text for s in segments if s.text)
            dur = segments[-1].end if segments else 0.0
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            self._health.record_success(ProviderCapability.TRANSCRIPT, latency_ms)

            actual_lang = translate_to if is_translated else matched_tr.language_code

            return TranscriptResult(
                video_id=clean_id,
                language=actual_lang,
                requested_language=language,
                actual_language=actual_lang,
                fallback_used=fallback_used,
                fallback_language=fallback_language if fallback_used else None,
                is_generated=matched_tr.is_generated,
                is_translated=is_translated,
                total_segments=len(segments),
                total_words=len(full_text.split()),
                duration_seconds=dur,
                segments=segments,
                full_text=full_text,
            )

        except (VideoUnavailable, InvalidVideoId) as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                str(e),
                is_systemic=False,
            )
            return None

        except (TranscriptsDisabled, NoTranscriptFound, VideoUnplayable) as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                str(e),
                is_systemic=False,
            )
            return None

        except (IpBlocked, RequestBlocked, PoTokenRequired) as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                f"Access blocked by YouTube anti-bot: {e}",
                is_systemic=True,
            )
            return None

        except Exception as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                f"Unexpected error in YouTubeTranscriptApi: {e}",
                is_systemic=True,
            )
            return None
