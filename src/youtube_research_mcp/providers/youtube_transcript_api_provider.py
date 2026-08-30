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
        self._api = YouTubeTranscriptApi()

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
            
            # Normalize target language codes
            lang_code = language.lower()
            lang_base = lang_code.split("-")[0]
            fb_code = fallback_language.lower() if fallback_language else None
            fb_base = fb_code.split("-")[0] if fb_code else None

            # Collect candidates: List[Tuple[Transcript, bool]] (transcript, is_fallback)
            candidates = []

            # 1. Exact / prefix match on requested language (manual tracks first, then generated)
            for code, t in getattr(transcript_list, "_manually_created_transcripts", {}).items():
                c_lower = code.lower()
                if c_lower == lang_code or c_lower.startswith(f"{lang_base}-") or lang_code.startswith(f"{c_lower}-"):
                    candidates.append((t, False))

            for code, t in getattr(transcript_list, "_generated_transcripts", {}).items():
                c_lower = code.lower()
                if c_lower == lang_code or c_lower.startswith(f"{lang_base}-") or lang_code.startswith(f"{c_lower}-"):
                    candidates.append((t, False))

            # 2. Fallback language (if requested and different)
            if fb_code and fb_code != lang_code:
                for code, t in getattr(transcript_list, "_manually_created_transcripts", {}).items():
                    c_lower = code.lower()
                    if c_lower == fb_code or c_lower.startswith(f"{fb_base}-") or fb_code.startswith(f"{c_lower}-"):
                        candidates.append((t, True))

                for code, t in getattr(transcript_list, "_generated_transcripts", {}).items():
                    c_lower = code.lower()
                    if c_lower == fb_code or c_lower.startswith(f"{fb_base}-") or fb_code.startswith(f"{c_lower}-"):
                        candidates.append((t, True))

            # 3. If translate_to is requested, any translatable transcript can serve as source
            if translate_to:
                for t in transcript_list:
                    if t not in [c[0] for c in candidates]:
                        candidates.append((t, True if fb_code else False))

            # 4. If fallback_language is specified but candidates empty, allow any transcript
            if fallback_language and not candidates:
                for t in transcript_list:
                    candidates.append((t, True))

            # Deduplicate candidates while preserving order
            unique_candidates = []
            seen = set()
            for t, is_fb in candidates:
                key = (t.language_code, t.is_generated)
                if key not in seen:
                    seen.add(key)
                    unique_candidates.append((t, is_fb))

            if not unique_candidates:
                try:
                    search_langs = [language]
                    if fallback_language:
                        search_langs.append(fallback_language)
                    t = transcript_list.find_transcript(search_langs)
                    unique_candidates.append((t, t.language_code.lower() != lang_code))
                except Exception:
                    pass

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
