import argparse
import logging
import os
import sys
from fastmcp import FastMCP

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.config import settings
from youtube_research_mcp.openai_connector import register_openai_connector
from youtube_research_mcp.services.router import get_router
from youtube_research_mcp.tools import register_all_tools

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(settings.MCP_SERVER_NAME)


def create_server() -> FastMCP:
    """Initialize FastMCP server and wire all tools, OpenAI connector, and resources."""
    mcp = FastMCP(
        name=settings.MCP_SERVER_NAME,
    )

    # Register all MCP tools
    register_all_tools(mcp)

    # Register OpenAI Plugin / Custom Connector endpoints
    register_openai_connector(mcp)

    # FastMCP Health Resource
    @mcp.resource("youtube://health")
    async def get_health_resource() -> str:
        """Returns real-time provider health scores, circuit breaker states, and latencies."""
        router = get_router()
        health_list = router.get_health_report()
        lines = ["# YouTube Research MCP — Provider Health Status", ""]
        for h in health_list:
            status_emoji = (
                "🟢 Healthy" if h.is_healthy else "🔴 Circuit Open / Degraded"
            )
            lines.append(f"### Provider: {h.provider_name} ({status_emoji})")
            lines.append(f"- **Total Requests**: {h.total_requests}")
            lines.append(f"- **Success Rate**: {h.success_rate * 100:.1f}%")
            lines.append(f"- **Average Latency**: {h.avg_latency_ms:.1f} ms")
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
        default=os.getenv("MCP_TRANSPORT", "http"),
        help="Transport protocol (default: http for ChatGPT / remote)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host for HTTP / SSE transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port for HTTP / SSE transport (default: 8000)",
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
