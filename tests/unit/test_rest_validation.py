import json
import pytest
from starlette.requests import Request
from youtube_research_mcp.openai_connector import register_openai_connector_routes
from youtube_research_mcp.config import settings


def make_post_request(path: str, body: dict) -> Request:
    raw_body = json.dumps(body).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": raw_body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(scope, receive=receive)


@pytest.mark.asyncio
async def test_rest_search_validation_empty_and_oversized():
    routes = {}

    class MockMCP:
        def custom_route(self, path, methods=None):
            def decorator(func):
                routes[path] = func
                return func
            return decorator

    mcp = MockMCP()
    register_openai_connector_routes(mcp)

    search_handler = routes["/api/search"]

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "RATE_LIMIT_ENABLED", False)

        # 1. Empty query -> 400 Bad Request
        req_empty = make_post_request("/api/search", {"query": ""})
        res_empty = await search_handler(req_empty)
        assert res_empty.status_code == 400
        assert "empty" in json.loads(res_empty.body)["message"]

        # 2. Oversized query (> 500 chars) -> 400 Bad Request
        req_large = make_post_request("/api/search", {"query": "A" * 600})
        res_large = await search_handler(req_large)
        assert res_large.status_code == 400
        assert "exceeds maximum" in json.loads(res_large.body)["message"]

        # 3. Invalid date format -> 400 Bad Request
        req_date = make_post_request("/api/search", {"query": "valid query", "published_after": "not-a-date"})
        res_date = await search_handler(req_date)
        assert res_date.status_code == 400
        assert "Invalid date format" in json.loads(res_date.body)["message"]


@pytest.mark.asyncio
async def test_rest_video_invalid_id():
    routes = {}

    class MockMCP:
        def custom_route(self, path, methods=None):
            def decorator(func):
                routes[path] = func
                return func
            return decorator

    mcp = MockMCP()
    register_openai_connector_routes(mcp)

    video_handler = routes["/api/video"]

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "RATE_LIMIT_ENABLED", False)

        # Invalid ID
        req_bad_id = make_post_request("/api/video", {"video_id": "invalid!!!"})
        res = await video_handler(req_bad_id)
        assert res.status_code == 400
        assert "Invalid YouTube video ID" in json.loads(res.body)["message"]
