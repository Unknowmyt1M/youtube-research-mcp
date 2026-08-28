from typing import Any, Dict, Optional
from fastmcp import Context
from pydantic import Field

from youtube_research_mcp.services.transcripts import TranscriptService

_transcript_service = TranscriptService()


def register_transcript_tools(mcp):
    """Register youtube_transcript tool on FastMCP server."""

    @mcp.tool(
        name="youtube_transcript",
        description=(
            "Extract the full spoken transcript of a YouTube video with timestamped segments. "
            "Supports auto-generated and manual captions, and on-the-fly translation. "
            "Use this tool when you need the complete spoken dialogue or want to read the transcript directly."
        ),
    )
    async def youtube_transcript(
        video_id: str = Field(
            description="11-character YouTube video ID or full YouTube URL"
        ),
        language: str = Field(
            default="en", description="Desired caption language code (e.g. 'en', 'es', 'hi')"
        ),
        include_timestamps: bool = Field(
            default=True,
            description="If true, returns structured segments with start/end timecodes and deep links. If false, returns clean text only.",
        ),
        translate_to: Optional[str] = Field(
            default=None,
            description="Optional target language code to translate captions into (e.g. 'es', 'fr', 'de')",
        ),
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx:
            await ctx.info(
                f"Fetching transcript for {video_id} (lang={language}, translate={translate_to})"
            )

        res = await _transcript_service.get_transcript(
            video_id_or_url=video_id,
            language=language,
            translate_to=translate_to,
        )

        if not res:
            return {
                "status": "error",
                "message": (
                    f"No captions available for video: {video_id}. Captions might be disabled by the creator, "
                    "or the requested language is unavailable."
                ),
            }

        dump = res.model_dump()
        if not include_timestamps:
            return {
                "video_id": dump["video_id"],
                "language": dump["language"],
                "total_words": dump["total_words"],
                "full_text": dump["full_text"],
            }

        return dump
