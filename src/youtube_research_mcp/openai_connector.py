import json
from typing import Any, Dict
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from youtube_research_mcp.models.research import ResearchDepth
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.services.research import ResearchEngine

_search_service = SearchService()
_metadata_service = MetadataService()
_transcript_service = TranscriptService()
_research_engine = ResearchEngine()


def get_openapi_schema(base_url: str) -> Dict[str, Any]:
    """Generate OpenAPI 3.1.0 specification for ChatGPT Plugin/Connector."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "YouTube Research Engine",
            "description": "Fast, reliable, API-keyless YouTube knowledge extraction and deep research for AI agents.",
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
                                        "query": {"type": "string", "description": "Search keywords or topic"},
                                        "max_results": {"type": "integer", "default": 5, "description": "Max results (1-25)"},
                                        "language": {"type": "string", "default": "en", "description": "Language code"},
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
                        }
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
                        }
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
                        }
                    },
                }
            },
            "/api/find_in_video": {
                "post": {
                    "summary": "Find Topic Inside Video",
                    "description": "Pinpoint exact sections and timestamps in a long video where a topic is discussed using Hybrid RRF semantic search.",
                    "operationId": "youtube_find_in_video",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "video_id": {"type": "string", "description": "11-character video ID or full URL"},
                                        "query": {"type": "string", "description": "Specific question or topic to locate"},
                                        "max_results": {"type": "integer", "default": 5, "description": "Number of matches"},
                                    },
                                    "required": ["video_id", "query"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful matched sections",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/api/research": {
                "post": {
                    "summary": "Multi-Video Research Engine",
                    "description": "Autonomous multi-video research and cross-video evidence synthesis with timestamp deep links and near-duplicate clustering.",
                    "operationId": "youtube_research",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Broad topic to research across YouTube"},
                                        "depth": {"type": "string", "enum": ["quick", "standard", "deep"], "default": "standard"},
                                        "max_videos_per_channel": {"type": "integer", "default": 2},
                                    },
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Successful multi-video evidence",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
        },
    }


def register_openai_connector(mcp):
    """Register ChatGPT Plugin / Connector manifest, OpenAPI spec, and REST endpoints."""

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }

    # Root landing & health
    @mcp.custom_route("/", methods=["GET", "OPTIONS"])
    async def root_route(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        return JSONResponse(
            {
                "status": "online",
                "name": "YouTube Research Engine",
                "version": "2.0.0",
                "description": "Fast, reliable, API-keyless YouTube knowledge extraction and deep research.",
                "mcp_endpoint": "/mcp",
                "openapi_endpoint": "/openapi.json",
                "plugin_manifest": "/.well-known/ai-plugin.json",
            },
            headers=cors_headers,
        )

    # OpenAI Plugin Manifest
    @mcp.custom_route("/.well-known/ai-plugin.json", methods=["GET", "OPTIONS"])
    async def ai_plugin_manifest(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        manifest = {
            "schema_version": "v1",
            "name_for_human": "YouTube Research",
            "name_for_model": "youtube_research",
            "description_for_human": "Search YouTube, get timestamped transcripts, and pinpoint exact video sections with zero API keys.",
            "description_for_model": (
                "Search YouTube, extract video transcripts, pinpoint sections in long videos with deep links (?t=XX), "
                "and perform multi-video research."
            ),
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base_url}/openapi.json",
            },
            "logo_url": "https://www.youtube.com/s/desktop/f7b0f699/img/favicon_144x144.png",
            "contact_email": "support@example.com",
            "legal_info_url": "https://example.com/legal",
        }
        return JSONResponse(manifest, headers=cors_headers)

    # OpenAPI JSON Schema
    @mcp.custom_route("/openapi.json", methods=["GET", "OPTIONS"])
    async def openapi_json_route(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        schema = get_openapi_schema(base_url)
        return JSONResponse(schema, headers=cors_headers)

    # REST: /api/search
    @mcp.custom_route("/api/search", methods=["POST", "OPTIONS"])
    async def api_search(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        try:
            body = await request.json()
        except Exception:
            body = {}
        query = body.get("query", "")
        max_res = body.get("max_results", 5)
        lang = body.get("language", "en")
        p_after = body.get("published_after")
        p_before = body.get("published_before")
        res = await _search_service.search(
            query=query,
            max_results=max_res,
            language=lang,
            published_after=p_after,
            published_before=p_before,
        )
        return JSONResponse(res.model_dump(), headers=cors_headers)

    # REST: /api/video
    @mcp.custom_route("/api/video", methods=["POST", "OPTIONS"])
    async def api_video(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        try:
            body = await request.json()
        except Exception:
            body = {}
        vid = body.get("video_id", "")
        res = await _metadata_service.get_video_overview(vid)
        if not res:
            return JSONResponse({"status": "error", "message": f"Could not find video: {vid}"}, status_code=404, headers=cors_headers)
        return JSONResponse(res.model_dump(), headers=cors_headers)

    # REST: /api/transcript
    @mcp.custom_route("/api/transcript", methods=["POST", "OPTIONS"])
    async def api_transcript(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        try:
            body = await request.json()
        except Exception:
            body = {}
        vid = body.get("video_id", "")
        lang = body.get("language", "en")
        fb_lang = body.get("fallback_language", "en")
        inc_ts = body.get("include_timestamps", True)
        trans = body.get("translate_to")
        res = await _transcript_service.get_transcript(
            vid, language=lang, fallback_language=fb_lang, translate_to=trans
        )
        if not res:
            return JSONResponse({"status": "error", "message": f"No captions found for video: {vid}"}, status_code=404, headers=cors_headers)
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
                headers=cors_headers,
            )
        return JSONResponse(dump, headers=cors_headers)

    # REST: /api/find_in_video
    @mcp.custom_route("/api/find_in_video", methods=["POST", "OPTIONS"])
    async def api_find_in_video(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        try:
            body = await request.json()
        except Exception:
            body = {}
        vid = body.get("video_id", "")
        q = body.get("query", "")
        max_res = body.get("max_results", 5)
        matches = await _transcript_service.find_in_video(vid, query=q, max_results=max_res)
        return JSONResponse({"status": "success", "video_id": vid, "matches": [m.model_dump() for m in matches]}, headers=cors_headers)

    # REST: /api/research
    @mcp.custom_route("/api/research", methods=["POST", "OPTIONS"])
    async def api_research(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        try:
            body = await request.json()
        except Exception:
            body = {}
        q = body.get("query", "")
        d_str = body.get("depth", "standard")
        try:
            depth = ResearchDepth(d_str)
        except ValueError:
            depth = ResearchDepth.STANDARD
        max_per_ch = body.get("max_videos_per_channel", 2)
        res = await _research_engine.research_topic(
            q, depth=depth, max_videos_per_channel=max_per_ch
        )
        return JSONResponse(res.model_dump(), headers=cors_headers)
