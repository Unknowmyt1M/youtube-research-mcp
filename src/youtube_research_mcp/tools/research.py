from typing import Any, Dict, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.models.research import ResearchDepth
from youtube_research_mcp.services.research import ResearchEngine

_research_engine = ResearchEngine()


def register_research_tools(mcp):
    """Register high-level youtube_research multi-video synthesis tool on FastMCP server."""

    @mcp.tool(
        name="youtube_research",
        description=(
            "Autonomous multi-video research tool. Discovers relevant YouTube videos across diverse channels, "
            "extracts spoken transcripts concurrently, performs semantic search, and aggregates timestamped citations "
            "with near-duplicate claim clustering."
        ),
    )
    async def youtube_research(
        query: str = Field(
            description="Broad research topic, question, or technology to investigate across YouTube"
        ),
        depth: ResearchDepth = Field(
            default=ResearchDepth.STANDARD,
            description="Research depth: 'quick' (2 videos), 'standard' (3 videos), or 'deep' (5 videos)",
        ),
        max_videos_per_channel: int = Field(
            default=2, ge=1, le=5, description="Maximum videos to include from any single channel (source diversity)"
        ),
        language: str = Field(
            default="en", description="Target video search and transcript language"
        ),
        fallback_language: Optional[str] = Field(
            default="en", description="Fallback transcript language if requested language is unavailable"
        ),
        published_after: Optional[str] = Field(
            default=None, description="Optional ISO date filter (YYYY-MM-DD) to research only recent videos"
        ),
        published_before: Optional[str] = Field(
            default=None, description="Optional ISO date filter (YYYY-MM-DD)"
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx:
            await ctx.info(
                f"Starting multi-video research on '{query}' (depth={depth.value}, max_per_channel={max_videos_per_channel})"
            )

        res = await _research_engine.research_topic(
            query=query,
            depth=depth,
            max_videos_per_channel=max_videos_per_channel,
            language=language,
            fallback_language=fallback_language,
            published_after=published_after,
            published_before=published_before,
        )
        return res.model_dump()
