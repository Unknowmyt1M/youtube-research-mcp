import json
from typing import Any, Dict, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.research import ResearchDepth
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.services.research import ResearchEngine
from youtube_research_mcp.utils.rate_limit import get_rate_limiter
from youtube_research_mcp.utils.security import extract_video_id
from youtube_research_mcp.utils.validation import (
    validate_date_filter,
    validate_language_code,
    validate_max_results,
    validate_query,
)

_search_service = SearchService()
_metadata_service = MetadataService()
_transcript_service = TranscriptService()
_research_engine = ResearchEngine()


def get_public_cors_headers(request: Request) -> Dict[str, str]:
    """Calculate CORS headers for public API and ChatGPT connector endpoints."""
    origin = request.headers.get("origin", "").strip()
    headers: Dict[str, str] = {
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, X-Requested-With",
    }
    if settings.CORS_ALLOW_ALL_API:
        headers["Access-Control-Allow-Origin"] = "*"
    elif origin and origin in settings.CORS_ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    elif settings.CORS_ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = settings.CORS_ALLOWED_ORIGINS[0]
    return headers


async def check_rate_limit(request: Request, cors_headers: Dict[str, str]) -> Optional[Response]:
    """Check request rate limits and return 429 Too Many Requests if bucket is empty."""
    if not settings.RATE_LIMIT_ENABLED:
        return None
    limiter = get_rate_limiter()
    allowed = await limiter.try_acquire(1.0)
    if not allowed:
        return JSONResponse(
            {
                "status": "error",
                "message": f"Rate limit exceeded (Maximum {settings.RATE_LIMIT_RPS} requests/second). Please try again shortly.",
            },
            status_code=429,
            headers=cors_headers,
        )
    return None


def get_openapi_schema(base_url: str) -> Dict[str, Any]:
    """Generate OpenAPI 3.1.0 specification for ChatGPT Plugin/Connector."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Nexora Research Engine",
            "description": "Fast, reliable, API-keyless YouTube and video knowledge extraction and deep research for AI agents.",
            "version": "v2.0.0",
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/api/search": {
                "post": {
                    "summary": "Search YouTube Videos",
                    "description": "Search YouTube for videos matching a query without needing an API key.",
                    "operationId": "youtube_search",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Search keywords or topic (max 500 chars)"},
                                        "max_results": {"type": "integer", "default": 5, "description": "Max results (1-25)"},
                                        "language": {"type": "string", "default": "en", "description": "ISO 639 language code"},
                                        "published_after": {"type": "string", "description": "ISO date filter YYYY-MM-DD"},
                                        "published_before": {"type": "string", "description": "ISO date filter YYYY-MM-DD"},
                                    },
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful search results",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Validation error"},
                        "429": {"description": "Rate limit exceeded"},
                    },
                }
            },
            "/api/video": {
                "post": {
                    "summary": "Get Video Metadata & Chapters",
                    "description": "Retrieve complete metadata, view statistics, duration, and chapters for a YouTube video.",
                    "operationId": "youtube_video",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "video_id": {"type": "string", "description": "11-character video ID or full URL"},
                                    },
                                    "required": ["video_id"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful metadata",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Invalid video ID"},
                        "404": {"description": "Video not found"},
                    },
                }
            },
            "/api/transcript": {
                "post": {
                    "summary": "Get Video Transcript",
                    "description": "Extract full spoken dialogue with timestamped segments and explicit language provenance.",
                    "operationId": "youtube_transcript",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "video_id": {"type": "string", "description": "11-character video ID or full URL"},
                                        "language": {"type": "string", "default": "en", "description": "Caption language"},
                                        "fallback_language": {"type": "string", "default": "en", "description": "Fallback language if primary unavailable"},
                                        "include_timestamps": {"type": "boolean", "default": True, "description": "Include timestamps"},
                                        "translate_to": {"type": "string", "description": "Optional translation language"},
                                    },
                                    "required": ["video_id"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful transcript",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Invalid parameters"},
                        "404": {"description": "Captions not found"},
                    },
                }
            },
            "/api/find_in_video": {
                "post": {
                    "summary": "Find Topic Inside Video",
                    "description": "Pinpoint exact timestamped quotes inside a YouTube video using Hybrid RRF semantic retrieval.",
                    "operationId": "youtube_find_in_video",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "video_id": {"type": "string", "description": "11-character video ID or full URL"},
                                        "query": {"type": "string", "description": "Topic, question, or concept to find (max 500 chars)"},
                                        "max_results": {"type": "integer", "default": 5, "description": "Max sections (1-10)"},
                                        "language": {"type": "string", "default": "en", "description": "Caption language"},
                                    },
                                    "required": ["video_id", "query"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Matching spoken quotes",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Validation error"},
                    },
                }
            },
            "/api/research": {
                "post": {
                    "summary": "Multi-Video Deep Research",
                    "description": "Synthesize knowledge across multiple diverse YouTube channels with claim clustering.",
                    "operationId": "youtube_research",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Research topic (max 500 chars)"},
                                        "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "default": "standard"},
                                        "max_videos_per_channel": {"type": "integer", "default": 2, "description": "Max videos per creator (1-5)"},
                                        "published_after": {"type": "string", "description": "ISO date filter YYYY-MM-DD"},
                                        "published_before": {"type": "string", "description": "ISO date filter YYYY-MM-DD"},
                                    },
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Multi-video research synthesis with clustered evidence",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                        "400": {"description": "Validation error"},
                    },
                }
            },
        },
    }


def register_openai_connector_routes(mcp):
    """Register ChatGPT Plugin, Custom GPT manifest, OpenAPI schema, and hardened REST endpoints."""

    # 0. Root Service Info & Fast Cloud Health Check
    @mcp.custom_route("/", methods=["GET", "OPTIONS"])
    async def root_service_info(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)
        return JSONResponse(
            {
                "status": "healthy",
                "service": settings.PRODUCT_NAME,
                "legacy_name": settings.MCP_SERVER_NAME,
                "tagline": settings.TAGLINE,
                "protocol": "mcp-2024-11-05",
                "transport": "streamable-http",
                "mcp_endpoint": "/mcp",
                "docs": "/openapi.json",
            },
            headers=cors,
        )

    @mcp.custom_route("/health", methods=["GET", "OPTIONS"])
    async def health_check_route(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)
        return JSONResponse(
            {
                "status": "healthy",
                "service": settings.PRODUCT_NAME,
                "legacy_name": settings.MCP_SERVER_NAME,
                "version": "v2.0.0-2026-09-04-v5",
            },
            headers=cors,
        )

    # 1. ChatGPT Plugin Manifest
    @mcp.custom_route("/.well-known/ai-plugin.json", methods=["GET", "OPTIONS"])
    async def ai_plugin_manifest(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        manifest = {
            "schema_version": "v1",
            "name_for_human": "Nexora YouTube Intelligence",
            "name_for_model": "nexora_mcp",
            "description_for_human": "Search YouTube, extract transcripts with timestamps, pinpoint topics, and conduct multi-video research with Nexora.",
            "description_for_model": (
                "Nexora video intelligence engine. Search videos, fetch metadata/chapters, retrieve full timestamped transcripts, "
                "pinpoint exact spoken dialogue sections using hybrid BM25+vector RRF retrieval, and synthesize multi-video research topics."
            ),
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base_url}/openapi.json",
                "is_user_authenticated": False,
            },
            "logo_url": f"{base_url}/logo.png",
            "contact_email": "support@antigravity.ai",
            "legal_info_url": f"{base_url}/terms",
        }
        return JSONResponse(manifest, headers=cors)

    # 2. OpenAPI JSON Schema
    @mcp.custom_route("/openapi.json", methods=["GET", "OPTIONS"])
    async def openapi_json_route(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        schema = get_openapi_schema(base_url)
        return JSONResponse(schema, headers=cors)

    # 3. REST: /api/search
    @mcp.custom_route("/api/search", methods=["POST", "OPTIONS"])
    async def api_search(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        rate_err = await check_rate_limit(request, cors)
        if rate_err:
            return rate_err

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error", "message": "Invalid JSON request body."}, status_code=400, headers=cors)

        try:
            query = validate_query(body.get("query"), field_name="query")
            max_res = validate_max_results(body.get("max_results", 5), min_val=1, max_val=25, default=5)
            lang = validate_language_code(body.get("language", "en"), default="en") or "en"
            p_after = validate_date_filter(body.get("published_after"))
            p_before = validate_date_filter(body.get("published_before"))

            res = await _search_service.search(
                query=query,
                max_results=max_res,
                language=lang,
                published_after=p_after,
                published_before=p_before,
            )
            return JSONResponse(res.model_dump(), headers=cors)
        except ValueError as ve:
            return JSONResponse({"status": "error", "message": str(ve)}, status_code=400, headers=cors)

    # 4. REST: /api/video
    @mcp.custom_route("/api/video", methods=["POST", "OPTIONS"])
    async def api_video(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        rate_err = await check_rate_limit(request, cors)
        if rate_err:
            return rate_err

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error", "message": "Invalid JSON request body."}, status_code=400, headers=cors)

        raw_vid = body.get("video_id", "")
        try:
            vid = extract_video_id(raw_vid)
        except ValueError as ve:
            return JSONResponse({"status": "error", "message": str(ve)}, status_code=400, headers=cors)

        res = await _metadata_service.get_video_overview(vid)
        if not res:
            return JSONResponse({"status": "error", "message": f"Could not find video: {vid}"}, status_code=404, headers=cors)
        return JSONResponse(res.model_dump(), headers=cors)

    # 5. REST: /api/transcript
    @mcp.custom_route("/api/transcript", methods=["POST", "OPTIONS"])
    async def api_transcript(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        rate_err = await check_rate_limit(request, cors)
        if rate_err:
            return rate_err

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error", "message": "Invalid JSON request body."}, status_code=400, headers=cors)

        raw_vid = body.get("video_id", "")
        try:
            vid = extract_video_id(raw_vid)
            lang = validate_language_code(body.get("language", "en"), default="en") or "en"
            fb_lang = validate_language_code(body.get("fallback_language", "en"), default="en", allow_none=True)
            trans = validate_language_code(body.get("translate_to"), default=None, allow_none=True)
            inc_ts = bool(body.get("include_timestamps", True))
        except ValueError as ve:
            return JSONResponse({"status": "error", "message": str(ve)}, status_code=400, headers=cors)

        res = await _transcript_service.get_transcript(
            vid, language=lang, fallback_language=fb_lang, translate_to=trans
        )
        if not res:
            return JSONResponse({"status": "error", "message": f"No captions found for video: {vid}"}, status_code=404, headers=cors)
        dump = res.model_dump()
        if not inc_ts:
            return JSONResponse(
                {
                    "video_id": dump["video_id"],
                    "requested_language": dump["requested_language"],
                    "actual_language": dump["actual_language"],
                    "fallback_used": dump["fallback_used"],
                    "total_words": dump["total_words"],
                    "full_text": dump["full_text"],
                },
                headers=cors,
            )
        return JSONResponse(dump, headers=cors)

    # 6. REST: /api/find_in_video
    @mcp.custom_route("/api/find_in_video", methods=["POST", "OPTIONS"])
    async def api_find_in_video(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        rate_err = await check_rate_limit(request, cors)
        if rate_err:
            return rate_err

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error", "message": "Invalid JSON request body."}, status_code=400, headers=cors)

        raw_vid = body.get("video_id", "")
        try:
            vid = extract_video_id(raw_vid)
            q = validate_query(body.get("query"), field_name="query")
            max_res = validate_max_results(body.get("max_results", 5), min_val=1, max_val=10, default=5)
            lang = validate_language_code(body.get("language", "en"), default="en") or "en"
        except ValueError as ve:
            return JSONResponse({"status": "error", "message": str(ve)}, status_code=400, headers=cors)

        matches = await _transcript_service.find_in_video(vid, query=q, max_results=max_res, language=lang)
        return JSONResponse({"status": "success", "video_id": vid, "matches": [m.model_dump() for m in matches]}, headers=cors)

    # 7. REST: /api/research
    @mcp.custom_route("/api/research", methods=["POST", "OPTIONS"])
    async def api_research(request: Request) -> Response:
        cors = get_public_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        rate_err = await check_rate_limit(request, cors)
        if rate_err:
            return rate_err

        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"status": "error", "message": "Invalid JSON request body."}, status_code=400, headers=cors)

        try:
            q = validate_query(body.get("query"), field_name="query")
            d_str = body.get("depth", "standard")
            try:
                depth = ResearchDepth(d_str)
            except ValueError:
                depth = ResearchDepth.STANDARD
            max_per_ch = validate_max_results(body.get("max_videos_per_channel", 2), min_val=1, max_val=5, default=2)
            pub_after = validate_date_filter(body.get("published_after"))
            pub_before = validate_date_filter(body.get("published_before"))
            lang = validate_language_code(body.get("language", "en"), default="en") or "en"

            res = await _research_engine.research_topic(
                q,
                depth=depth,
                max_videos_per_channel=max_per_ch,
                published_after=pub_after,
                published_before=pub_before,
                language=lang,
            )
            return JSONResponse(res.model_dump(), headers=cors)
        except ValueError as ve:
            return JSONResponse({"status": "error", "message": str(ve)}, status_code=400, headers=cors)


register_openai_connector = register_openai_connector_routes
