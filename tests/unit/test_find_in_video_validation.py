import pytest
from unittest.mock import AsyncMock, patch
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.tools.find_in_video import register_find_in_video_tools


@pytest.mark.asyncio
async def test_find_in_video_empty_and_whitespace_service():
    """Verify TranscriptService.find_in_video returns empty list for empty/whitespace query."""
    service = TranscriptService()

    # Empty string
    res_empty = await service.find_in_video("dQw4w9WgXcQ", query="")
    assert res_empty == []

    # Whitespace strings
    assert await service.find_in_video("dQw4w9WgXcQ", query="   ") == []
    assert await service.find_in_video("dQw4w9WgXcQ", query="\n\t") == []


@pytest.mark.asyncio
async def test_find_in_video_tool_validation():
    """Verify the FastMCP tool returns explicit validation error response on empty/whitespace query."""
    tools = {}

    class MockMCP:
        def tool(self, **kwargs):
            def decorator(func):
                tools[kwargs.get("name", func.__name__)] = func
                return func
            return decorator

    mcp = MockMCP()
    register_find_in_video_tools(mcp)

    find_tool = tools["youtube_find_in_video"]

    # Test empty query
    res = await find_tool(video_id="dQw4w9WgXcQ", query="")
    assert res["status"] == "error"
    assert "non-empty string" in res["message"]
    assert res["matches"] == []

    # Test whitespace query
    res_ws = await find_tool(video_id="dQw4w9WgXcQ", query="   \n  ")
    assert res_ws["status"] == "error"
    assert res_ws["matches"] == []
