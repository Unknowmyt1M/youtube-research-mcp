from typing import Optional

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.video import VideoOverview
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.security import extract_video_id


class MetadataService:
    """Video metadata and structural chapter analysis service."""

    def __init__(self):
        self.router = get_router()
        self.cache = get_cache()

    async def get_video_overview(self, video_id_or_url: str) -> Optional[VideoOverview]:
        clean_id = extract_video_id(video_id_or_url)
        cache_key = f"metadata:{clean_id}"

        # Check Cache
        cached = await self.cache.get(cache_key)
        if cached:
            return VideoOverview(**cached)

        # Route to providers
        overview = await self.router.route_metadata(clean_id)
        if overview:
            await self.cache.set(
                cache_key,
                overview.model_dump(),
                ttl_seconds=settings.CACHE_TTL_METADATA,
                category="metadata",
            )
            return overview

        return None
