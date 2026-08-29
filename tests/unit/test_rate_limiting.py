import asyncio
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse
from youtube_research_mcp.openai_connector import check_rate_limit
from youtube_research_mcp.utils.rate_limit import AsyncTokenBucket
from youtube_research_mcp.config import settings


@pytest.mark.asyncio
async def test_token_bucket_try_acquire():
    """Verify non-blocking try_acquire allows up to burst and rejects when empty."""
    bucket = AsyncTokenBucket(rate=1.0, capacity=3.0)

    # Acquire 3 tokens immediately (burst capacity)
    assert await bucket.try_acquire(1.0) is True
    assert await bucket.try_acquire(1.0) is True
    assert await bucket.try_acquire(1.0) is True

    # 4th immediate token must fail
    assert await bucket.try_acquire(1.0) is False

    # Sleep 1.1 seconds -> 1 token replenishes
    await asyncio.sleep(1.1)
    assert await bucket.try_acquire(1.0) is True
    assert await bucket.try_acquire(1.0) is False


@pytest.mark.asyncio
async def test_check_rate_limit_helper_returns_429():
    """Verify check_rate_limit returns 429 response when rate limit is exceeded."""
    req = Request({"type": "http", "method": "POST", "path": "/api/search", "headers": []})
    cors = {"Access-Control-Allow-Origin": "*"}

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "RATE_LIMIT_ENABLED", True)
        from youtube_research_mcp.utils import rate_limit
        rate_limit._global_rate_limiter = AsyncTokenBucket(rate=1.0, capacity=1.0)

        # 1st request succeeds
        res1 = await check_rate_limit(req, cors)
        assert res1 is None

        # 2nd immediate request fails with 429
        res2 = await check_rate_limit(req, cors)
        assert isinstance(res2, JSONResponse)
        assert res2.status_code == 429
