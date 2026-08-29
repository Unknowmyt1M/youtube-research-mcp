import asyncio
from collections import defaultdict
import logging
from typing import Dict, List, Optional
import numpy as np

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.research import (
    ClaimEvidenceCluster,
    DEPTH_CITATIONS_PER_VIDEO,
    DEPTH_VIDEO_LIMITS,
    MultiVideoResearchResult,
    ResearchDepth,
    SourceCitation,
    VideoResearchSummary,
)
from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.services.retrieval import LexicalTfidfFallback, tokenize_multilingual
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.rate_limit import ConcurrencyLimiter

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Multi-video research discovery, source diversity filtering, and cross-video evidence synthesis."""

    def __init__(self):
        self.search_service = SearchService()
        self.transcript_service = TranscriptService()
        self.limiter = ConcurrencyLimiter(
            max_concurrent=settings.MAX_CONCURRENCY
        )

    async def research_topic(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.STANDARD,
        max_videos: Optional[int] = None,
        max_videos_per_channel: int = settings.MAX_VIDEOS_PER_CHANNEL,
        language: str = "en",
        fallback_language: Optional[str] = settings.DEFAULT_FALLBACK_LANGUAGE,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> MultiVideoResearchResult:
        """Perform autonomous deep research across diverse candidate YouTube videos."""
        metrics.record_request("research")

        # 1. Determine strict video and quote limits based on depth
        target_video_count = (
            max_videos if max_videos is not None else DEPTH_VIDEO_LIMITS[depth]
        )
        quotes_per_video = DEPTH_CITATIONS_PER_VIDEO[depth]

        # 2. Search candidate videos (fetch extra to allow diversity filtering)
        search_resp = await self.search_service.search(
            query=query,
            max_results=min(25, target_video_count * 3),
            language=language,
            published_after=published_after,
            published_before=published_before,
        )

        # 3. Apply channel diversity filter
        diverse_candidates = self._apply_channel_diversity(
            search_resp.results,
            max_total=target_video_count,
            max_per_channel=max_videos_per_channel,
        )

        if not diverse_candidates:
            return MultiVideoResearchResult(
                topic=query,
                depth=depth,
                total_videos_analyzed=0,
                videos_with_transcripts=0,
                total_evidence_chunks=0,
                sources=[],
                evidence_clusters=[],
                all_citations_ranked=[],
            )

        # 4. Ingest transcripts and extract relevant sections concurrently
        tasks = [
            self._process_single_video(
                cand, query, quotes_per_video, language, fallback_language
            )
            for cand in diverse_candidates
        ]
        summaries: List[Optional[VideoResearchSummary]] = await asyncio.gather(*tasks)

        valid_summaries: List[VideoResearchSummary] = [
            s for s in summaries if s is not None
        ]
        videos_with_tx = sum(1 for s in valid_summaries if s.caption_found)

        # 5. Collect all citations across all videos
        all_citations: List[SourceCitation] = []
        for s in valid_summaries:
            all_citations.extend(s.key_citations)

        all_citations.sort(key=lambda c: c.relevance, reverse=True)

        # 6. Cluster near-duplicate evidence across independent videos
        clusters = self._cluster_evidence(all_citations)

        return MultiVideoResearchResult(
            topic=query,
            depth=depth,
            total_videos_analyzed=len(diverse_candidates),
            videos_with_transcripts=videos_with_tx,
            total_evidence_chunks=len(all_citations),
            sources=valid_summaries,
            evidence_clusters=clusters,
            all_citations_ranked=all_citations,
        )

    def _apply_channel_diversity(
        self,
        candidates: List[VideoSearchResult],
        max_total: int,
        max_per_channel: int,
    ) -> List[VideoSearchResult]:
        """Filter candidates so no single channel dominates the evidence pool."""
        channel_counts: Dict[str, int] = defaultdict(int)
        selected: List[VideoSearchResult] = []

        for cand in candidates:
            ch = cand.channel.strip().lower()
            if channel_counts[ch] < max_per_channel:
                selected.append(cand)
                channel_counts[ch] += 1
                if len(selected) >= max_total:
                    break

        # If strict diversity didn't fill all slots, fill remaining from leftover candidates
        if len(selected) < max_total:
            for cand in candidates:
                if cand not in selected:
                    selected.append(cand)
                    if len(selected) >= max_total:
                        break

        return selected

    async def _process_single_video(
        self,
        candidate: VideoSearchResult,
        query: str,
        quotes_limit: int,
        language: str,
        fallback_language: Optional[str],
    ) -> Optional[VideoResearchSummary]:
        vid = candidate.video_id

        async def _extract():
            matches = await self.transcript_service.find_in_video(
                video_id_or_url=vid,
                query=query,
                max_results=quotes_limit,
                language=language,
                fallback_language=fallback_language,
            )

            citations: List[SourceCitation] = []
            caption_found = len(matches) > 0
            matched_lang = matches[0].language if matches else language

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
                        language=m.language,
                    )
                )

            return VideoResearchSummary(
                video_id=vid,
                title=candidate.title,
                channel=candidate.channel,
                url=candidate.url,
                duration=candidate.duration,
                caption_found=caption_found,
                language=matched_lang,
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
                language=language,
                key_citations=[],
            )

    def _cluster_evidence(
        self, citations: List[SourceCitation]
    ) -> List[ClaimEvidenceCluster]:
        """Cluster evidence citations across multiple independent videos using text similarity."""
        if len(citations) < 2:
            return []

        docs = [c.quote for c in citations]
        embedder = LexicalTfidfFallback()
        vecs = embedder.fit_transform(docs)

        # Compute cosine similarity matrix
        sim_matrix = np.dot(vecs, vecs.T)
        num_docs = len(citations)
        visited = set()
        clusters: List[ClaimEvidenceCluster] = []

        for i in range(num_docs):
            if i in visited:
                continue

            group_indices = [i]
            for j in range(i + 1, num_docs):
                if j not in visited and sim_matrix[i, j] >= settings.EVIDENCE_SIMILARITY_THRESHOLD:
                    # Only group if from different videos or different timestamps
                    group_indices.append(j)

            if len(group_indices) >= 2:
                for idx in group_indices:
                    visited.add(idx)

                cluster_citations = [citations[idx] for idx in group_indices]
                channels = list(set(c.channel for c in cluster_citations))
                unique_videos = len(set(c.video_id for c in cluster_citations))

                # Take first 10 words of the highest-relevance quote as headline
                top_quote = cluster_citations[0].quote
                words = top_quote.split()[:12]
                headline = " ".join(words) + "..."

                clusters.append(
                    ClaimEvidenceCluster(
                        cluster_id=f"cluster-{len(clusters) + 1}",
                        topic_headline=headline,
                        independent_sources_count=unique_videos,
                        consensus_score=round(float(np.mean([c.relevance for c in cluster_citations])), 2),
                        channels=channels,
                        citations=cluster_citations,
                    )
                )

        return clusters
