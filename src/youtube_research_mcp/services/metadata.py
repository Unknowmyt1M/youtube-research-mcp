from typing import Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.security import extract_video_id


class MetadataService:
    """Service for retrieving, parsing, and caching rich video metadata."""

    def __init__(self):
        self.router = get_router()
        self.cache = get_cache()

    async def get_video_overview(self, video_id_or_url: str) -> Optional[VideoOverview]:
        clean_id = extract_video_id(video_id_or_url)
        cache_key = f"metadata:{clean_id}"

        # 1. Check cache
        cached, is_neg = await self.cache.get_with_status(cache_key)
        if is_neg:
            metrics.record_cache_hit(is_negative=True)
            return None
        if cached:
            metrics.record_cache_hit()
            return VideoOverview.model_validate(cached)

        metrics.record_cache_miss()

        # 2. Fetch via router
        overview = await self.router.get_video(clean_id)
        if not overview:
            return None

        # 3. Store in cache
        await self.cache.set(
            cache_key, overview.model_dump(), ttl=settings.CACHE_TTL_METADATA
        )

        return overview
