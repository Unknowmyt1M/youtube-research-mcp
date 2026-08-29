import asyncio
import json
import secrets
import time
from typing import Any, Dict, List, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.cache.sqlite import SQLiteCache
from youtube_research_mcp.cache.redis import RedisCache
from youtube_research_mcp.cache.memory import MemoryCache
from youtube_research_mcp.config import settings
from youtube_research_mcp.providers.base import CircuitState, ProviderCapability
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import get_single_flight


def get_admin_cors_headers(request: Request) -> Dict[str, str]:
    """Calculate origin-validated CORS headers specifically for admin endpoints (no wildcard)."""
    origin = request.headers.get("origin", "").strip()
    headers: Dict[str, str] = {
        "Vary": "Origin",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Headers": "Authorization, X-Admin-Key, Content-Type, Accept",
    }
    if origin and origin in settings.CORS_ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    elif not origin and settings.CORS_ALLOWED_ORIGINS:
        # Same-origin or local non-browser tool
        headers["Access-Control-Allow-Origin"] = settings.CORS_ALLOWED_ORIGINS[0]
    return headers


def verify_admin_auth(request: Request) -> Optional[Response]:
    """Verify administrator authentication via Bearer token or X-Admin-Key header using constant-time comparison."""
    if not settings.ADMIN_API_KEY:
        # Development mode: No API key configured
        return None

    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("authorization", "").strip()
    provided_key = None
    if auth_header.lower().startswith("bearer "):
        provided_key = auth_header[7:].strip()
    elif "x-admin-key" in request.headers:
        provided_key = request.headers.get("x-admin-key", "").strip()

    if not provided_key:
        cors = get_admin_cors_headers(request)
        return JSONResponse(
            {
                "status": "error",
                "message": "Unauthorized: Missing admin authentication credentials (Bearer token or X-Admin-Key header required).",
            },
            status_code=401,
            headers=cors,
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, settings.ADMIN_API_KEY):
        cors = get_admin_cors_headers(request)
        return JSONResponse(
            {
                "status": "error",
                "message": "Forbidden: Invalid admin credentials provided.",
            },
            status_code=403,
            headers=cors,
        )

    return None


def register_admin_routes(mcp):
    """Register /api/admin REST routes for the complete administration dashboard."""

    # 1. System Config & Env
    @mcp.custom_route("/api/admin/config", methods=["GET", "OPTIONS"])
    async def admin_config(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

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
            "RATE_LIMIT_ENABLED": settings.RATE_LIMIT_ENABLED,
            "RATE_LIMIT_RPS": settings.RATE_LIMIT_RPS,
            "RATE_LIMIT_BURST": settings.RATE_LIMIT_BURST,
            "MAX_QUERY_LENGTH": settings.MAX_QUERY_LENGTH,
            "MAX_TRANSCRIPT_SEGMENTS": settings.MAX_TRANSCRIPT_SEGMENTS,
            "MAX_CACHE_ENTRIES": settings.MAX_CACHE_ENTRIES,
            "ADMIN_AUTH_ACTIVE": bool(settings.ADMIN_API_KEY),
        }
        return JSONResponse({"status": "success", "config": cfg}, headers=cors)

    # 2. Live Metrics & Telemetry
    @mcp.custom_route("/api/admin/metrics", methods=["GET", "OPTIONS"])
    async def admin_metrics(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

        data = metrics.get_summary()
        data["single_flight_coalesced_savings"] = get_single_flight().coalesced_count
        return JSONResponse({"status": "success", "metrics": data}, headers=cors)

    # 3. Cache Management: Purge & Clear
    @mcp.custom_route("/api/admin/cache/purge", methods=["POST", "OPTIONS"])
    async def admin_cache_purge(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

        cache = get_cache()
        count = await cache.purge_expired()
        return JSONResponse({"status": "success", "purged_count": count}, headers=cors)

    @mcp.custom_route("/api/admin/cache/clear", methods=["POST", "OPTIONS"])
    async def admin_cache_clear(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

        cache = get_cache()
        await cache.clear()
        return JSONResponse({"status": "success", "message": "All cache entries cleared"}, headers=cors)

    # 4. Cache Keys Explorer
    @mcp.custom_route("/api/admin/cache/keys", methods=["GET", "OPTIONS"])
    async def admin_cache_keys(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

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
                return JSONResponse({"status": "error", "message": str(e)}, status_code=500, headers=cors)
        elif isinstance(cache, RedisCache):
            try:
                client = await cache._get_client()
                version = settings.CACHE_SCHEMA_VERSION
                cursor = 0
                scanned_keys = []
                while len(scanned_keys) < 50:
                    cursor, keys = await client.scan(cursor=cursor, match=f"{version}:*", count=50)
                    scanned_keys.extend(keys)
                    if cursor == 0:
                        break
                now = time.time()
                for k in scanned_keys[:50]:
                    raw = await client.get(k)
                    ttl = await client.ttl(k)
                    is_neg = False
                    created_at = now
                    if raw:
                        try:
                            payload = json.loads(raw)
                            is_neg = bool(payload.get("is_negative", False))
                            created_at = payload.get("created_at", now)
                        except Exception:
                            pass
                    entries.append({
                        "key": k,
                        "is_negative": is_neg,
                        "expires_in_seconds": max(0, ttl) if ttl and ttl > 0 else 0,
                        "created_at": created_at,
                        "size_bytes": len(raw.encode("utf-8")) if raw else 0,
                    })
            except Exception as e:
                return JSONResponse({"status": "error", "message": f"Redis cache explorer error: {str(e)}"}, status_code=500, headers=cors)
        elif isinstance(cache, MemoryCache):
            now = time.time()
            async with cache._lock:
                for k, (val, is_neg, exp) in list(cache._store.items())[:50]:
                    entries.append({
                        "key": k,
                        "is_negative": is_neg,
                        "expires_in_seconds": max(0, int(exp - now)),
                        "created_at": now,
                        "size_bytes": len(str(val)),
                    })
        return JSONResponse({"status": "success", "total": len(entries), "entries": entries}, headers=cors)

    # 5. Circuit Breakers Inspector & Reset
    @mcp.custom_route("/api/admin/circuits", methods=["GET", "OPTIONS"])
    async def admin_circuits(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

        router = get_router()
        reports = router.get_health_report()
        return JSONResponse({"status": "success", "reports": [r.model_dump() for r in reports]}, headers=cors)

    @mcp.custom_route("/api/admin/circuits/reset", methods=["POST", "OPTIONS"])
    async def admin_circuits_reset(request: Request) -> Response:
        cors = get_admin_cors_headers(request)
        if request.method == "OPTIONS":
            return Response("", headers=cors)

        auth_err = verify_admin_auth(request)
        if auth_err:
            return auth_err

        router = get_router()
        for p in [router.ytdlp, router.innertube, router.commercial]:
            health = getattr(p, "_health", None)
            if health and hasattr(health, "breakers"):
                for b in health.breakers.values():
                    b.state = CircuitState.CLOSED
                    b.failure_count = 0
                    b.probe_in_flight = False
        return JSONResponse({"status": "success", "message": "All circuit breakers reset to CLOSED (Healthy)"}, headers=cors)
