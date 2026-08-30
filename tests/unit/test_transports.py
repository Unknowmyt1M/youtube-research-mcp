import pytest
from starlette.testclient import TestClient
from youtube_research_mcp.server import create_server


def test_fastmcp_server_initialization_and_transports():
    """Verify FastMCP server initializes cleanly with all tools and custom routes."""
    server = create_server()
    assert server.name == "youtube-research-mcp"

    app = server.http_app()
    client = TestClient(app)

    # 1. OpenAPI schema route
    resp_schema = client.get("/openapi.json")
    assert resp_schema.status_code == 200
    schema = resp_schema.json()
    assert "paths" in schema
    assert "/api/search" in schema["paths"]

    # 2. AI Plugin manifest
    resp_plugin = client.get("/.well-known/ai-plugin.json")
    assert resp_plugin.status_code == 200
    assert resp_plugin.json().get("schema_version") == "v1"

    # 3. Cloud Container Health Routes (GET / and GET /health)
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    root_json = resp_root.json()
    assert root_json.get("status") == "healthy"
    assert root_json.get("mcp_endpoint") == "/mcp"

    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    assert resp_health.json().get("status") == "healthy"

    # 4. Admin routes
    resp_admin = client.get("/api/admin/metrics")
    assert resp_admin.status_code in [200, 401, 403]


def test_effective_port_precedence():
    """Verify cloud PORT takes precedence over MCP_PORT, falling back to 8000."""
    from youtube_research_mcp.config import Settings

    # Default
    s1 = Settings()
    assert s1.effective_port == 8000

    # MCP_PORT set
    s2 = Settings(MCP_PORT=9000)
    assert s2.effective_port == 9000

    # Cloud platform PORT set (takes precedence)
    s3 = Settings(PORT=8080, MCP_PORT=9000)
    assert s3.effective_port == 8080

