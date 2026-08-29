from typing import Any, Dict, List, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.services.transcripts import TranscriptService

_transcript_service = TranscriptService()


def register_find_in_video_tools(mcp):
    """Register youtube_find_in_video hybrid semantic search tool on FastMCP server."""

    @mcp.tool(
        name="youtube_find_in_video",
        description=(
            "Pinpoint exact sections and timestamps in a long video where a specific topic or concept is discussed. "
            "Uses in-process Hybrid RRF (FastEmbed ONNX dense vectors + BM25 lexical search) to locate the most relevant 2-3 minute chunks. "
            "Returns deep-link timestamp URLs (e.g. ?t=842s), relevance scores, chapter context, and exact spoken quotes. "
            "PREFERRED over reading full transcripts for videos longer than 10 minutes."
        ),
    )
    async def youtube_find_in_video(
        video_id: str = Field(
            description="11-character YouTube video ID or full YouTube URL"
        ),
        query: str = Field(
            description="The specific question, topic, or concept to find inside the video"
        ),
        max_results: int = Field(
            default=5, ge=1, le=10, description="Number of relevant sections to retrieve (1-10)"
        ),
        language: str = Field(
            default="en", description="Transcript language code"
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        clean_query = query.strip() if query else ""
        if not clean_query:
            return {
                "status": "error",
                "message": "Query parameter must be a non-empty string.",
                "matches": [],
            }

        if ctx:
            await ctx.info(
                f"Searching for '{clean_query}' in video {video_id} using Hybrid RRF"
            )

        matches = await _transcript_service.find_in_video(
            video_id_or_url=video_id,
            query=clean_query,
            max_results=max_results,
            language=language,
        )

        if not matches:
            return {
                "status": "not_found",
                "message": (
                    f"No relevant spoken sections matching '{query}' were found in video: {video_id}. "
                    "Ensure the video has captions enabled."
                ),
                "matches": [],
            }

        return {
            "status": "success",
            "video_id": video_id,
            "query": query,
            "total_matches": len(matches),
            "matches": [m.model_dump() for m in matches],
        }
