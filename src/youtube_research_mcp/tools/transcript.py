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
            "Extract the spoken transcript of a YouTube video with timestamped segments and language provenance. "
            "Returns requested_language, actual_language, and fallback_used flags. "
            "Never silently swaps languages unless fallback_language is specified."
        ),
    )
    async def youtube_transcript(
        video_id: str = Field(
            description="11-character YouTube video ID or full YouTube URL"
        ),
        language: str = Field(
            default="en", description="Desired caption language code (e.g. 'en', 'hi', 'es')"
        ),
        fallback_language: Optional[str] = Field(
            default="en",
            description="Language code to use ONLY IF the requested language is completely unavailable (set to null/None to disable fallback)",
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
                f"Fetching transcript for {video_id} (lang={language}, fallback={fallback_language})"
            )

        res = await _transcript_service.get_transcript(
            video_id_or_url=video_id,
            language=language,
            fallback_language=fallback_language,
            translate_to=translate_to,
        )

        if not res:
            return {
                "status": "error",
                "message": (
                    f"No captions available for video: {video_id} in language '{language}' (fallback='{fallback_language}'). "
                    "Captions might be disabled by the creator or unavailable in the requested language."
                ),
            }

        dump = res.model_dump()
        if not include_timestamps:
            return {
                "video_id": dump["video_id"],
                "requested_language": dump["requested_language"],
                "actual_language": dump["actual_language"],
                "fallback_used": dump["fallback_used"],
                "total_words": dump["total_words"],
                "full_text": dump["full_text"],
            }

        return dump
