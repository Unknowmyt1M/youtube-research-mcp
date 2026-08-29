import asyncio
import json
import time
from typing import Any, Dict, List
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.cache.sqlite import SQLiteCache
from youtube_research_mcp.config import settings
from youtube_research_mcp.providers.base import CircuitState, ProviderCapability
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import get_single_flight


def register_admin_routes(mcp):
    """Register /api/admin REST routes for the complete administration dashboard."""
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Headers": "*",
    }

    # 1. System Config & Env
    @mcp.custom_route("/api/admin/config", methods=["GET", "OPTIONS"])
    async def admin_config(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        cfg = {
            "CACHE_BACKEND": settings.CACHE_BACKEND,
            "CACHE_DB_PATH": str(settings.CACHE_DB_PATH),
            "CACHE_TTL_SEARCH": settings.CACHE_TTL_SEARCH,
            "CACHE_TTL_METADATA": settings.CACHE_TTL_METADATA,
            "CACHE_TTL_TRANSCRIPT": settings.CACHE_TTL_TRANSCRIPT,
            "NEGATIVE_CACHE_TTL": settings.NEGATIVE_CACHE_TTL,
            "CIRCUIT_BREAKER_FAIL_THRESHOLD": settings.CIRCUIT_BREAKER_FAIL_THRESHOLD,
            "CIRCUIT_BREAKER_COOLDOWN_SECONDS": settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
            "MAX_CONCURRENCY": settings.MAX_CONCURRENCY,
            "DEFAULT_FALLBACK_LANGUAGE": settings.DEFAULT_FALLBACK_LANGUAGE,
            "MAX_VIDEOS_PER_CHANNEL": settings.MAX_VIDEOS_PER_CHANNEL,
            "USE_ONNX_EMBEDDER": settings.USE_ONNX_EMBEDDER,
            "EMBEDDING_MODEL": settings.EMBEDDING_MODEL,
            "BM25_K1": settings.BM25_K1,
            "BM25_B": settings.BM25_B,
            "MAX_RETRIEVAL_INDEXES": settings.MAX_RETRIEVAL_INDEXES,
            "INDEX_TTL_SECONDS": settings.INDEX_TTL_SECONDS,
        }
        return JSONResponse({"status": "success", "config": cfg}, headers=cors_headers)

    # 2. Live Metrics & Telemetry
    @mcp.custom_route("/api/admin/metrics", methods=["GET", "OPTIONS"])
    async def admin_metrics(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        data = metrics.get_summary()
        data["single_flight_coalesced_savings"] = get_single_flight().coalesced_count
        return JSONResponse({"status": "success", "metrics": data}, headers=cors_headers)

    # 3. Cache Management: Purge & Clear
    @mcp.custom_route("/api/admin/cache/purge", methods=["POST", "OPTIONS"])
    async def admin_cache_purge(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        cache = get_cache()
        count = await cache.purge_expired()
        return JSONResponse({"status": "success", "purged_count": count}, headers=cors_headers)

    @mcp.custom_route("/api/admin/cache/clear", methods=["POST", "OPTIONS"])
    async def admin_cache_clear(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        cache = get_cache()
        await cache.clear()
        return JSONResponse({"status": "success", "message": "All cache entries cleared"}, headers=cors_headers)

    # 4. Cache Keys Explorer
    @mcp.custom_route("/api/admin/cache/keys", methods=["GET", "OPTIONS"])
    async def admin_cache_keys(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        cache = get_cache()
        entries = []
        if isinstance(cache, SQLiteCache):
            try:
                import aiosqlite
                async with aiosqlite.connect(cache.db_path) as db:
                    async with db.execute(
                        "SELECT key, is_negative, expires_at, created_at, length(value) as size_bytes FROM cache_store ORDER BY created_at DESC LIMIT 50"
                    ) as cursor:
                        rows = await cursor.fetchall()
                        now = time.time()
                        for row in rows:
                            entries.append({
                                "key": row[0],
                                "is_negative": bool(row[1]),
                                "expires_in_seconds": max(0, int(row[2] - now)),
                                "created_at": row[3],
                                "size_bytes": row[4] or 0,
                            })
            except Exception as e:
                return JSONResponse({"status": "error", "message": str(e)}, status_code=500, headers=cors_headers)
        return JSONResponse({"status": "success", "total": len(entries), "entries": entries}, headers=cors_headers)

    # 5. Circuit Breakers Inspector & Reset
    @mcp.custom_route("/api/admin/circuits", methods=["GET", "OPTIONS"])
    async def admin_circuits(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        router = get_router()
        reports = router.get_health_report()
        return JSONResponse({"status": "success", "reports": [r.model_dump() for r in reports]}, headers=cors_headers)

    @mcp.custom_route("/api/admin/circuits/reset", methods=["POST", "OPTIONS"])
    async def admin_circuits_reset(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response("", headers=cors_headers)
        router = get_router()
        for p in [router.ytdlp, router.innertube, router.commercial]:
            health = getattr(p, "_health", None)
            if health and hasattr(health, "breakers"):
                for b in health.breakers.values():
                    b.state = CircuitState.CLOSED
                    b.failure_count = 0
                    b.probe_in_flight = False
        return JSONResponse({"status": "success", "message": "All circuit breakers reset to CLOSED (Healthy)"}, headers=cors_headers)
