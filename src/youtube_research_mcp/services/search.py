from datetime import datetime, timedelta
import logging
import re
from typing import List, Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.search import SearchResponse, VideoSearchResult
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.metrics import metrics

logger = logging.getLogger(__name__)


class SearchService:
    """Service orchestrating search queries, caching, and deterministic post-filtering."""

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
        sanitized_query = re.sub(r"\s+", " ", query.strip())
        cache_key = f"search:{sanitized_query.lower()}:{max_results}:{language}:{published_after}:{published_before}"

        # 1. Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            metrics.record_cache_hit()
            return SearchResponse.model_validate(cached)

        metrics.record_cache_miss()

        # 2. Fetch results via router
        # Fetch slightly more if post-filters are active
        fetch_limit = max_results * 2 if (published_after or published_before) else max_results
        raw_results = await self.router.search(
            query=sanitized_query,
            max_results=min(25, max(max_results, fetch_limit)),
            language=language,
            published_after=published_after,
            published_before=published_before,
        )

        # 3. Deterministic local post-filtering
        filtered = self._apply_post_filters(
            raw_results,
            published_after=published_after,
            published_before=published_before,
        )

        final_results = filtered[:max_results]
        resp = SearchResponse(
            query=sanitized_query,
            total_results=len(final_results),
            results=final_results,
        )

        # 4. Cache response
        await self.cache.set(
            cache_key, resp.model_dump(), ttl=settings.CACHE_TTL_SEARCH
        )

        return resp

    def _apply_post_filters(
        self,
        results: List[VideoSearchResult],
        published_after: Optional[str],
        published_before: Optional[str],
    ) -> List[VideoSearchResult]:
        """Apply deterministic date filtering on parsed relative or ISO timestamps."""
        if not published_after and not published_before:
            return results

        dt_after = self._parse_iso_date(published_after) if published_after else None
        dt_before = self._parse_iso_date(published_before) if published_before else None

        filtered: List[VideoSearchResult] = []
        for r in results:
            est_date = self._estimate_published_date(r.published_time)
            if est_date is None:
                # Keep if cannot determine date
                filtered.append(r)
                continue

            if dt_after and est_date < dt_after:
                continue
            if dt_before and est_date > dt_before:
                continue

            filtered.append(r)

        return filtered

    def _parse_iso_date(self, date_str: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def _estimate_published_date(self, pub_str: Optional[str]) -> Optional[datetime]:
        if not pub_str:
            return None

        # Check if already ISO / YYYYMMDD
        iso = self._parse_iso_date(pub_str)
        if iso:
            return iso

        now = datetime.now()
        low = pub_str.lower()

        # Parse relative strings like "3 days ago", "2 weeks ago", "1 month ago", "2 years ago"
        m = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)", low)
        if not m:
            return None

        val = int(m.group(1))
        unit = m.group(2)

        if "minute" in unit:
            return now - timedelta(minutes=val)
        elif "hour" in unit:
            return now - timedelta(hours=val)
        elif "day" in unit:
            return now - timedelta(days=val)
        elif "week" in unit:
            return now - timedelta(weeks=val)
        elif "month" in unit:
            return now - timedelta(days=val * 30)
        elif "year" in unit:
            return now - timedelta(days=val * 365)

        return None
