import pytest
from starlette.requests import Request
from youtube_research_mcp.admin_routes import get_admin_cors_headers
from youtube_research_mcp.openai_connector import get_public_cors_headers
from youtube_research_mcp.config import settings


def create_mock_request(origin: str = "") -> Request:
    header_list = []
    if origin:
        header_list.append((b"origin", origin.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "OPTIONS",
        "path": "/api/admin/config",
        "headers": header_list,
    }
    return Request(scope)


def test_admin_cors_allowed_origin():
    """Admin CORS should echo the specific allowed origin from CORS_ALLOWED_ORIGINS and not use wildcard."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CORS_ALLOWED_ORIGINS", ["http://localhost:5173"])
        req = create_mock_request(origin="http://localhost:5173")
        headers = get_admin_cors_headers(req)
        assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
        assert headers.get("Access-Control-Allow-Credentials") == "true"
        assert headers.get("Access-Control-Allow-Origin") != "*"


def test_admin_cors_disallowed_origin():
    """Admin CORS should reject / omit Access-Control-Allow-Origin for untrusted external origins."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CORS_ALLOWED_ORIGINS", ["http://localhost:5173"])
        req = create_mock_request(origin="https://malicious-site.com")
        headers = get_admin_cors_headers(req)
        assert "Access-Control-Allow-Origin" not in headers


def test_public_cors_wildcard_when_configured():
    """Public API endpoints should allow wildcard when CORS_ALLOW_ALL_API is true for ChatGPT."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "CORS_ALLOW_ALL_API", True)
        req = create_mock_request(origin="https://chatgpt.com")
        headers = get_public_cors_headers(req)
        assert headers.get("Access-Control-Allow-Origin") == "*"
