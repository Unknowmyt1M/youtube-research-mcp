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
            
            # Build language search priority
            search_langs = [language]
            if fallback_language and fallback_language != language:
                search_langs.append(fallback_language)
            
            matched_transcript = None
            fallback_used = False

            # Try finding requested language
            try:
                matched_transcript = transcript_list.find_transcript(search_langs)
                if matched_transcript.language_code != language and fallback_language:
                    fallback_used = True
            except Exception:
                # If specific language not found, try any available transcript
                try:
                    matched_transcript = next(iter(transcript_list))
                    fallback_used = True
                except StopIteration:
                    return None, None, False

            if not matched_transcript:
                return None, None, False

            # Handle translation if requested
            is_translated = False
            if translate_to and matched_transcript.is_translatable:
                try:
                    matched_transcript = matched_transcript.translate(translate_to)
                    is_translated = True
                except Exception as tr_err:
                    logger.warning(f"Translation to {translate_to} failed: {tr_err}")

            # Fetch the actual transcript snippets
            fetched_data = matched_transcript.fetch()
            return matched_transcript, fetched_data, fallback_used, is_translated

        try:
            matched_tr, fetched_data, fallback_used, is_translated = await asyncio.to_thread(_fetch_sync)
            
            if not matched_tr or not fetched_data:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT,
                    "No captions found in requested language",
                    category=ErrorCategory.NO_CAPTIONS,
                )
                return None

            snippets = fetched_data.snippets if hasattr(fetched_data, "snippets") else fetched_data
            if not snippets:
                self._health.record_failure(
                    ProviderCapability.TRANSCRIPT,
                    "Empty transcript snippets returned",
                    category=ErrorCategory.NO_CAPTIONS,
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
                category=ErrorCategory.VIDEO_NOT_FOUND,
            )
            return None

        except (TranscriptsDisabled, NoTranscriptFound, VideoUnplayable) as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                str(e),
                category=ErrorCategory.NO_CAPTIONS,
            )
            return None

        except (IpBlocked, RequestBlocked, PoTokenRequired) as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                f"Access blocked by YouTube anti-bot: {e}",
                category=ErrorCategory.BOT_DETECTION,
            )
            return None

        except Exception as e:
            self._health.record_failure(
                ProviderCapability.TRANSCRIPT,
                f"Unexpected error in YouTubeTranscriptApi: {e}",
                category=ErrorCategory.TRANSIENT_NETWORK,
            )
            return None
