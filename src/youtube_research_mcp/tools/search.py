from typing import Any, Dict, List, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.services.search import SearchService

_search_service = SearchService()


def register_search_tools(mcp):
    """Register youtube_search tool on FastMCP server."""

    @mcp.tool(
        name="youtube_search",
        description=(
            "Search YouTube for videos matching a query without needing an API key. "
            "Returns a structured list of videos with IDs, titles, channels, durations, views, and URLs. "
            "Use this tool when you need to discover videos on a topic or find candidate videos for research."
        ),
    )
    async def youtube_search(
        query: str = Field(description="Search keywords or research topic"),
        max_results: int = Field(
            default=5, ge=1, le=25, description="Maximum number of video results to return (1-25)"
        ),
        language: str = Field(
            default="en", description="Preferred language code (e.g. 'en', 'es', 'hi')"
        ),
        published_after: Optional[str] = Field(
            default=None, description="Optional ISO date filter (YYYY-MM-DD)"
        ),
        published_before: Optional[str] = Field(
            default=None, description="Optional ISO date filter (YYYY-MM-DD)"
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx:
            await ctx.info(f"Searching YouTube for: {query} (limit={max_results})")

        resp = await _search_service.search(
            query=query,
            max_results=max_results,
            language=language,
            published_after=published_after,
            published_before=published_before,
        )
        return resp.model_dump()
