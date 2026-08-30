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

    # 3. Admin routes
    resp_admin = client.get("/api/admin/metrics")
    assert resp_admin.status_code in [200, 401, 403]
