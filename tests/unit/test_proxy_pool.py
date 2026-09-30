import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from youtube_research_mcp.proxy_pool.config import config
from youtube_research_mcp.proxy_pool.fetcher import ProxyFetcher
from youtube_research_mcp.proxy_pool.validator import ProxyValidator
from youtube_research_mcp.proxy_pool.manager import ProxyPoolManager


@pytest.mark.asyncio
async def test_proxy_fetcher_regex_and_formatting():
    """Verify raw proxy strings are correctly cleaned, typed, and deduplicated."""
    sample_text = """
    # Comments should be ignored
    123.45.67.89:8080
    http://111.222.33.44:3128
    socks5://55.66.77.88:1080
    invalid_string_not_a_proxy
    123.45.67.89:8080
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_text

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    proxies = await ProxyFetcher.fetch_source(mock_client, "https://mocksource.com/list.txt")
    assert "http://123.45.67.89:8080" in proxies
    assert "http://111.222.33.44:3128" in proxies
    assert "socks5://55.66.77.88:1080" in proxies
    assert len(proxies) == 4  # Includes the duplicate parsed lines before set conversion


@pytest.mark.asyncio
async def test_proxy_validator_youtube_target():
    """Verify ProxyValidator tests against YouTube InnerTube endpoint correctly."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Mock successful YouTube player response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"playabilityStatus": {"status": "OK"}}
        mock_post.return_value = mock_resp

        lat = await ProxyValidator.validate_proxy("http://1.2.3.4:8080")
        assert lat is not None
        assert isinstance(lat, float)

        # Mock failed / blocked YouTube response
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"error": "blocked"}
        lat_failed = await ProxyValidator.validate_proxy("http://5.6.7.8:8080")
        assert lat_failed is None


@pytest.mark.asyncio
async def test_proxy_pool_manager_lifecycle_and_eviction():
    """Verify ProxyPoolManager round-robin selection, success tracking, and failure eviction."""
    mgr = ProxyPoolManager()
    mgr._pool = [
        {"proxy": "http://10.0.0.1:8080", "latency": 0.5, "consecutive_failures": 0},
        {"proxy": "http://10.0.0.2:8080", "latency": 0.8, "consecutive_failures": 0},
    ]

    # Test round-robin
    p1 = await mgr.get_proxy()
    p2 = await mgr.get_proxy()
    p3 = await mgr.get_proxy()
    assert p1 == "http://10.0.0.1:8080"
    assert p2 == "http://10.0.0.2:8080"
    assert p3 == "http://10.0.0.1:8080"

    # Test failure recording and eviction
    await mgr.report_failure("http://10.0.0.1:8080")
    assert mgr.pool_size == 2

    # Second failure should evict (config.MAX_CONSECUTIVE_FAILURES = 2)
    await mgr.report_failure("http://10.0.0.1:8080")
    assert mgr.pool_size == 1
    assert mgr._pool[0]["proxy"] == "http://10.0.0.2:8080"

    # Test success resets failure counter
    await mgr.report_failure("http://10.0.0.2:8080")
    assert mgr._pool[0]["consecutive_failures"] == 1
    await mgr.report_success("http://10.0.0.2:8080")
    assert mgr._pool[0]["consecutive_failures"] == 0
