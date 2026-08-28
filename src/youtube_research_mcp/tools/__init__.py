from youtube_research_mcp.tools.search import register_search_tools
from youtube_research_mcp.tools.video import register_video_tools
from youtube_research_mcp.tools.transcript import register_transcript_tools
from youtube_research_mcp.tools.find_in_video import register_find_in_video_tools
from youtube_research_mcp.tools.research import register_research_tools


def register_all_tools(mcp):
    """Register all YouTube Research MCP tools onto FastMCP instance."""
    register_search_tools(mcp)
    register_video_tools(mcp)
    register_transcript_tools(mcp)
    register_find_in_video_tools(mcp)
    register_research_tools(mcp)


__all__ = ["register_all_tools"]
