import hashlib
import time
from typing import List, Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import SearchResponse, VideoSearchResult
from youtube_research_mcp.services.router import get_router


class SearchService:
    """High-level YouTube search service with multi-tier failover and caching."""

    def __init__(self):
        self.router = get_router()
        self.cache = get_cache()

    async def search(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> SearchResponse:
        clean_query = query.strip()
        if not clean_query:
            return SearchResponse(query=query, total_results=0, results=[])

        # Generate cache key
        cache_params = f"{clean_query}_{max_results}_{language}_{published_after}_{published_before}"
        cache_key = (
            f"search:{hashlib.sha256(cache_params.encode()).hexdigest()}"
        )

        # Check Cache
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            results = [VideoSearchResult(**item) for item in cached_data]
            return SearchResponse(
                query=clean_query, total_results=len(results), results=results
            )

        # Query Multi-Tier Router
        raw_results = await self.router.route_search(
            query=clean_query,
            max_results=max_results,
            language=language,
            published_after=published_after,
            published_before=published_before,
        )

        # Rank and deduplicate
        ranked = self._rank_search_results(clean_query, raw_results)

        # Save to Cache
        if ranked:
            await self.cache.set(
                cache_key,
                [r.model_dump() for r in ranked],
                ttl_seconds=settings.CACHE_TTL_SEARCH,
                category="search",
            )

        return SearchResponse(
            query=clean_query, total_results=len(ranked), results=ranked
        )

    def _rank_search_results(
        self, query: str, results: List[VideoSearchResult]
    ) -> List[VideoSearchResult]:
        """Apply relevance scoring and deduplication."""
        seen_ids = set()
        unique_results: List[VideoSearchResult] = []

        query_tokens = set(query.lower().split())

        for r in results:
            if r.video_id in seen_ids:
                continue
            seen_ids.add(r.video_id)

            # Compute lexical title overlap score
            title_tokens = set(r.title.lower().split())
            overlap = len(query_tokens.intersection(title_tokens))
            base_score = 0.5 + (0.5 * (overlap / max(1, len(query_tokens))))

            # Slight duration boost for research videos (between 5m and 60m)
            if r.duration_seconds:
                if 300 <= r.duration_seconds <= 3600:
                    base_score += 0.05
                elif r.duration_seconds < 60:
                    base_score -= 0.1  # Downrank ultra-short clips for research

            r.relevance_score = round(min(1.0, max(0.1, base_score)), 2)
            unique_results.append(r)

        # Sort by relevance score
        unique_results.sort(
            key=lambda x: x.relevance_score or 0.0, reverse=True
        )
        return unique_results
