import asyncio
from typing import List, Optional

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.research import (
    MultiVideoResearchResult,
    SourceCitation,
    VideoResearchSummary,
)
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.utils.rate_limit import ConcurrencyLimiter


class ResearchEngine:
    """Multi-video research discovery, parallel ingestion, and cross-video evidence synthesis."""

    def __init__(self):
        self.search_service = SearchService()
        self.transcript_service = TranscriptService()
        self.limiter = ConcurrencyLimiter(
            max_concurrent=settings.MAX_CONCURRENCY
        )

    async def research_topic(
        self,
        query: str,
        max_videos: int = 5,
        depth: str = "standard",
    ) -> MultiVideoResearchResult:
        """Perform autonomous deep research across multiple YouTube videos."""
        # 1. Search candidate videos
        search_limit = min(15, max_videos * 2 if depth == "deep" else max_videos)
        search_resp = await self.search_service.search(
            query=query, max_results=search_limit
        )

        candidates = search_resp.results[:max_videos]
        if not candidates:
            return MultiVideoResearchResult(
                topic=query,
                depth=depth,
                total_videos_analyzed=0,
                videos_with_transcripts=0,
                total_evidence_chunks=0,
                sources=[],
                all_citations_ranked=[],
            )

        # 2. Parallel transcript extraction and in-video hybrid search
        tasks = [
            self._process_single_video(cand, query, depth)
            for cand in candidates
        ]
        summaries: List[Optional[VideoResearchSummary]] = await asyncio.gather(*tasks)

        valid_summaries: List[VideoResearchSummary] = [
            s for s in summaries if s is not None
        ]
        videos_with_tx = sum(1 for s in valid_summaries if s.caption_found)

        # 3. Collect and sort all citations across all videos
        all_citations: List[SourceCitation] = []
        for s in valid_summaries:
            all_citations.extend(s.key_citations)

        all_citations.sort(key=lambda c: c.relevance, reverse=True)

        return MultiVideoResearchResult(
            topic=query,
            depth=depth,
            total_videos_analyzed=len(candidates),
            videos_with_transcripts=videos_with_tx,
            total_evidence_chunks=len(all_citations),
            sources=valid_summaries,
            all_citations_ranked=all_citations,
        )

    async def _process_single_video(
        self, candidate, query: str, depth: str
    ) -> Optional[VideoResearchSummary]:
        vid = candidate.video_id
        top_k = 4 if depth == "deep" else 2

        async def _extract():
            matches = await self.transcript_service.find_in_video(
                video_id_or_url=vid,
                query=query,
                max_results=top_k,
            )

            citations: List[SourceCitation] = []
            caption_found = len(matches) > 0

            for m in matches:
                citations.append(
                    SourceCitation(
                        video_id=vid,
                        video_title=candidate.title,
                        channel=candidate.channel,
                        start_seconds=m.start_seconds,
                        end_seconds=m.end_seconds,
                        time_range=m.time_range,
                        url_with_timestamp=m.url,
                        quote=m.text,
                        relevance=m.relevance_score,
                    )
                )

            return VideoResearchSummary(
                video_id=vid,
                title=candidate.title,
                channel=candidate.channel,
                url=candidate.url,
                duration=candidate.duration,
                caption_found=caption_found,
                key_citations=citations,
            )

        try:
            return await self.limiter.run(_extract())
        except Exception:
            return VideoResearchSummary(
                video_id=vid,
                title=candidate.title,
                channel=candidate.channel,
                url=candidate.url,
                duration=candidate.duration,
                caption_found=False,
                key_citations=[],
            )
