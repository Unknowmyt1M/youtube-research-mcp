from typing import Any, Dict, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.services.metadata import MetadataService

_metadata_service = MetadataService()


def register_video_tools(mcp):
    """Register youtube_video metadata tool on FastMCP server."""

    @mcp.tool(
        name="youtube_video",
        description=(
            "Retrieve complete metadata, view statistics, tags, chapters, and caption availability for a specific YouTube video. "
            "Use this tool to inspect a video's table of contents (chapters) and determine if spoken transcripts are available."
        ),
    )
    async def youtube_video(
        video_id: str = Field(
            description="11-character YouTube video ID or full YouTube URL"
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx:
            await ctx.info(f"Fetching video metadata for: {video_id}")

        overview = await _metadata_service.get_video_overview(video_id)
        if not overview:
            return {
                "status": "error",
                "message": f"Could not retrieve metadata for video: {video_id}. It may be private or deleted.",
            }
        return overview.model_dump()
