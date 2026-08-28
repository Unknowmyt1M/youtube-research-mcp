from typing import Any, Dict, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.services.research import ResearchEngine

_research_engine = ResearchEngine()


def register_research_tools(mcp):
    """Register high-level youtube_research multi-video synthesis tool on FastMCP server."""

    @mcp.tool(
        name="youtube_research",
        description=(
            "Autonomous multi-video research tool. Discovers relevant YouTube videos on a topic, "
            "extracts transcripts concurrently, performs semantic search across all candidate videos, "
            "and aggregates timestamped citations with source provenance. "
            "Use this tool when the user wants to research a topic across multiple videos and compare what creators say."
        ),
    )
    async def youtube_research(
        query: str = Field(
            description="Broad research topic, question, or technology to investigate across YouTube"
        ),
        max_videos: int = Field(
            default=5, ge=1, le=10, description="Number of candidate videos to analyze (1-10)"
        ),
        depth: str = Field(
            default="standard", description="Research depth: 'quick' (top 2 quotes/video), 'standard' (top 3 quotes/video), or 'deep' (top 5 quotes/video)"
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx:
            await ctx.info(
                f"Starting multi-video research on '{query}' (analyzing up to {max_videos} videos)"
            )

        res = await _research_engine.research_topic(
            query=query,
            max_videos=max_videos,
            depth=depth,
        )
        return res.model_dump()
