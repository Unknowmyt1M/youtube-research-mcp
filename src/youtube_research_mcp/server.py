import argparse
from contextlib import asynccontextmanager
import logging
import os
import sys
from fastmcp import FastMCP

from youtube_research_mcp.admin_routes import register_admin_routes
from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.openai_connector import register_openai_connector
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.tools import register_all_tools
from youtube_research_mcp.utils.metrics import metrics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(settings.MCP_SERVER_NAME)


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage server startup and graceful connection pool shutdown."""
    cache = get_cache()
    # Purge expired cache entries on startup
    try:
        purged = await cache.purge_expired()
        logger.info(f"Purged {purged} expired cache entries on startup.")
    except Exception:
        pass

    yield

    # Clean up router and provider connection pools
    router = get_router()
    await router.close()
    logger.info("Closed provider HTTP connection pools.")

    # Clean up cache connection pool
    try:
        await cache.close()
        logger.info("Closed cache connection pool.")
    except Exception:
        pass


def create_server() -> FastMCP:
    """Initialize FastMCP server and wire all tools, OpenAPI connector, and resources."""
    mcp = FastMCP(
        name=settings.MCP_SERVER_NAME,
        lifespan=server_lifespan,
    )

    # Register all MCP tools
    register_all_tools(mcp)

    # Register OpenAI Plugin / Custom Connector endpoints
    register_openai_connector(mcp)

    # Register Admin Dashboard API routes
    register_admin_routes(mcp)

    # FastMCP Health Resource
    @mcp.resource("youtube://health")
    async def get_health_resource() -> str:
        """Returns real-time provider health, circuit breaker states, and metrics telemetry."""
        router = get_router()
        health_list = router.get_health_report()
        summary = metrics.get_summary()

        lines = [
            f"# {settings.PRODUCT_NAME} ({settings.MCP_SERVER_NAME}) — System Health & Telemetry",
            "",
            f"**Uptime**: {summary['uptime_seconds']}s | **Total Requests**: {sum(summary['requests'].values())}",
            f"**Cache Hit Rate**: {summary['cache']['hit_rate_pct']}% ({summary['cache']['hits']} hits, {summary['cache']['misses']} misses, {summary['cache']['negative_hits']} negative hits)",
            f"**Single-Flight Coalesced**: {summary['single_flight_coalesced']} concurrent requests saved",
            f"**Avg Retrieval Latency**: {summary['retrieval']['avg_latency_ms']} ms",
            "",
            "## Provider Capability Health & Circuit Breakers",
            "",
        ]

        for h in health_list:
            status_emoji = (
                "🟢 Healthy" if h.is_healthy else "🔴 Circuit Tripped / Degraded"
            )
            lines.append(f"### Provider: {h.provider_name} ({status_emoji})")
            lines.append(f"- **Total Requests**: {h.total_requests}")
            lines.append(f"- **Success Rate**: {h.success_rate * 100:.1f}%")
            lines.append(f"- **Average Latency**: {h.avg_latency_ms:.1f} ms")
            for cap_name, cap_data in h.capabilities.items():
                cap_state = cap_data["state"]
                lines.append(
                    f"  - `Capability: {cap_name}`: State={cap_state}, Success={cap_data['success_rate']}%, AvgLat={cap_data['avg_latency_ms']}ms"
                )
            if not h.is_healthy and h.last_failure_reason:
                lines.append(f"- **Last Failure**: {h.last_failure_reason}")
            lines.append("")

        return "\n".join(lines)

    return mcp


def main():
    """Main entrypoint supporting stdio, HTTP (Streamable HTTP for ChatGPT), and SSE."""
    parser = argparse.ArgumentParser(
        description="YouTube Research MCP Server"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=os.getenv("MCP_TRANSPORT", settings.MCP_TRANSPORT),
        help="Transport protocol (default: http for ChatGPT / remote)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", settings.MCP_HOST),
        help="Host for HTTP / SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.effective_port,
        help="Port for HTTP / SSE transport (checks PORT, MCP_PORT, default: 8000)",
    )

    args = parser.parse_args()
    server = create_server()

    if args.transport == "stdio":
        logger.info(
            f"Starting {settings.MCP_SERVER_NAME} over stdio transport..."
        )
        server.run(transport="stdio")
    elif args.transport == "http":
        logger.info(
            f"Starting {settings.MCP_SERVER_NAME} Streamable HTTP server on http://{args.host}:{args.port}/mcp ..."
        )
        server.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        logger.info(
            f"Starting {settings.MCP_SERVER_NAME} SSE server on http://{args.host}:{args.port}/sse ..."
        )
        server.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
