import logging
import time
from typing import List, Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import (
    TranscriptResult,
    TranscriptSearchMatch,
)
from youtube_research_mcp.services.chunker import TranscriptChunker
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.retrieval import get_retrieval_index
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.security import extract_video_id

logger = logging.getLogger(__name__)


class TranscriptService:
    """Service managing transcript extraction, language provenance, caching, and hybrid in-video search."""

    def __init__(self):
        self.router = get_router()
        self.cache = get_cache()
        self.metadata_service = MetadataService()
        self.chunker = TranscriptChunker(
            target_words=settings.CHUNK_TARGET_WORDS,
            overlap_words=settings.CHUNK_OVERLAP_WORDS,
        )

    async def get_transcript(
        self,
        video_id_or_url: str = "",
        language: str = "en",
        fallback_language: Optional[str] = settings.DEFAULT_FALLBACK_LANGUAGE,
        translate_to: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        target = video_id if video_id else video_id_or_url
        clean_id = extract_video_id(target)
        cache_key = f"transcript:{clean_id}:{language}:{fallback_language}:{translate_to}"

        # 1. Check cache
        cached, is_neg = await self.cache.get_with_status(cache_key)
        if is_neg:
            metrics.record_cache_hit(is_negative=True)
            return None
        if cached:
            metrics.record_cache_hit()
            return TranscriptResult.model_validate(cached)

        metrics.record_cache_miss()

        # 2. Fetch via router
        res = await self.router.get_transcript(
            video_id=clean_id,
            language=language,
            fallback_language=fallback_language,
            translate_to=translate_to,
        )

        if not res or not res.segments:
            # Negative cache for uncaptioned videos
            await self.cache.set_negative(
                cache_key,
                reason=f"No captions available for {clean_id} (lang={language})",
                ttl=settings.NEGATIVE_CACHE_TTL,
            )
            return None

        # 3. Store in cache
        await self.cache.set(
            cache_key, res.model_dump(), ttl=settings.CACHE_TTL_TRANSCRIPT
        )

        return res

    async def find_in_video(
        self,
        video_id_or_url: str = "",
        query: str = "",
        max_results: int = 5,
        language: str = "en",
        fallback_language: Optional[str] = settings.DEFAULT_FALLBACK_LANGUAGE,
        video_id: Optional[str] = None,
    ) -> List[TranscriptSearchMatch]:
        start_t = time.perf_counter()
        target = video_id if video_id else video_id_or_url
        clean_id = extract_video_id(target)

        # 1. Get transcript
        res = await self.get_transcript(
            video_id_or_url=clean_id,
            language=language,
            fallback_language=fallback_language,
        )
        if not res or not res.segments:
            return []

        # 2. Fetch chapters for context enhancement
        overview = await self.metadata_service.get_video_overview(clean_id)
        chapters = overview.chapters if overview else []

        # 3. Build semantic chunks
        chunks = self.chunker.chunk_transcript(
            video_id=clean_id,
            segments=res.segments,
            chapters=chapters,
        )

        if not chunks:
            return []

        # 4. Search using bounded RetrievalIndex
        index = get_retrieval_index(clean_id, chunks)
        matches = index.search(query=query, top_k=max_results, k_rrf=settings.RRF_K)

        for m in matches:
            m.language = res.actual_language

        latency_ms = (time.perf_counter() - start_t) * 1000.0
        metrics.record_retrieval(len(matches), latency_ms)

        return matches
