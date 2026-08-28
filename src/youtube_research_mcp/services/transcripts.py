from typing import List, Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import (
    TranscriptChunk,
    TranscriptResult,
    TranscriptSearchMatch,
)
from youtube_research_mcp.services.chunker import TranscriptChunker
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.retrieval import HybridRetrievalIndex
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.security import extract_video_id


class TranscriptService:
    """Transcript retrieval, caching, chunking, and in-video hybrid search service."""

    def __init__(self):
        self.router = get_router()
        self.cache = get_cache()
        self.chunker = TranscriptChunker(
            target_words=settings.CHUNK_TARGET_WORDS,
            overlap_words=settings.CHUNK_OVERLAP_WORDS,
        )
        self.metadata_service = MetadataService()
        self._indices: dict[str, HybridRetrievalIndex] = {}

    async def get_transcript(
        self,
        video_id_or_url: str,
        language: str = "en",
        translate_to: Optional[str] = None,
    ) -> Optional[TranscriptResult]:
        clean_id = extract_video_id(video_id_or_url)
        cache_key = f"transcript:{clean_id}:{language}:{translate_to or 'orig'}"

        # Check Cache
        cached = await self.cache.get(cache_key)
        if cached:
            return TranscriptResult(**cached)

        # Route extraction through provider router
        transcript = await self.router.route_transcript(
            video_id=clean_id,
            language=language,
            translate_to=translate_to,
        )

        if transcript and transcript.segments:
            await self.cache.set(
                cache_key,
                transcript.model_dump(),
                ttl_seconds=settings.CACHE_TTL_TRANSCRIPT,
                category="transcript",
            )
            return transcript

        return None

    async def get_chunks(
        self,
        video_id_or_url: str,
        language: str = "en",
    ) -> List[TranscriptChunk]:
        """Fetch transcript and produce timestamped semantic chunks."""
        clean_id = extract_video_id(video_id_or_url)
        transcript = await self.get_transcript(clean_id, language=language)
        if not transcript or not transcript.segments:
            return []

        # Fetch chapters for context enrichment if available
        overview = await self.metadata_service.get_video_overview(clean_id)
        chapters = overview.chapters if overview else None

        return self.chunker.chunk_transcript(
            clean_id, transcript.segments, chapters=chapters
        )

    async def find_in_video(
        self,
        video_id_or_url: str,
        query: str,
        max_results: int = 5,
        language: str = "en",
    ) -> List[TranscriptSearchMatch]:
        """Pinpoint search within a single video transcript using Hybrid RRF retrieval."""
        clean_id = extract_video_id(video_id_or_url)
        chunks = await self.get_chunks(clean_id, language=language)
        if not chunks:
            return []

        # Build or retrieve in-memory hybrid index for video
        index_key = f"{clean_id}:{language}"
        if index_key not in self._indices:
            self._indices[index_key] = HybridRetrievalIndex(chunks)

        index = self._indices[index_key]
        return index.search(query=query, top_k=max_results)
