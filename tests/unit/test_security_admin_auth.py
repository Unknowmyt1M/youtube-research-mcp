import pytest
from unittest.mock import MagicMock
from starlette.requests import Request
from starlette.responses import JSONResponse
from youtube_research_mcp.admin_routes import verify_admin_auth
from youtube_research_mcp.config import settings


def create_mock_request(headers=None) -> Request:
    header_list = []
    if headers:
        for k, v in headers.items():
            header_list.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/admin/config",
        "headers": header_list,
    }
    return Request(scope)


def test_admin_auth_dev_mode():
    """When ADMIN_API_KEY is None (dev mode), requests pass without credentials."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "ADMIN_API_KEY", None)
        req = create_mock_request()
        err = verify_admin_auth(req)
        assert err is None


def test_admin_auth_missing_key():
    """When ADMIN_API_KEY is set and request lacks credentials, return 401."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "ADMIN_API_KEY", "super_secret_admin_key_123")
        req = create_mock_request()
        err = verify_admin_auth(req)
        assert isinstance(err, JSONResponse)
        assert err.status_code == 401


def test_admin_auth_invalid_key():
    """When ADMIN_API_KEY is set and wrong key is sent, return 403."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "ADMIN_API_KEY", "super_secret_admin_key_123")
        req = create_mock_request(headers={"Authorization": "Bearer wrong_key"})
        err = verify_admin_auth(req)
        assert isinstance(err, JSONResponse)
        assert err.status_code == 403


def test_admin_auth_valid_bearer_token():
    """When ADMIN_API_KEY matches Authorization Bearer token, return None."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "ADMIN_API_KEY", "super_secret_admin_key_123")
        req = create_mock_request(headers={"Authorization": "Bearer super_secret_admin_key_123"})
        err = verify_admin_auth(req)
        assert err is None


def test_admin_auth_valid_x_admin_key_header():
    """When ADMIN_API_KEY matches X-Admin-Key header, return None."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "ADMIN_API_KEY", "super_secret_admin_key_123")
        req = create_mock_request(headers={"X-Admin-Key": "super_secret_admin_key_123"})
        err = verify_admin_auth(req)
        assert err is None
