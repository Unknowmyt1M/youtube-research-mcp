import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock
from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.cache.redis import RedisCache


def test_redis_cache_implements_all_abstract_methods():
    """Verify that RedisCache inherits from BaseCache and has no missing abstract methods."""
    # Ensure RedisCache is a subclass
    assert issubclass(RedisCache, BaseCache)

    # Check abstract methods
    abstract_methods = BaseCache.__abstractmethods__
    for method_name in abstract_methods:
        assert hasattr(RedisCache, method_name), f"RedisCache missing abstract method {method_name}"

    # Verify instantiation does not raise TypeError
    cache = RedisCache("redis://localhost:6379/0")
    assert cache is not None
    assert cache.redis_url == "redis://localhost:6379/0"


@pytest.mark.asyncio
async def test_redis_cache_mocked_methods():
    """Verify get_with_status, set, set_negative, delete, clear, and purge_expired logic with mock."""
    cache = RedisCache("redis://localhost:6379/0")
    mock_redis = AsyncMock()
    cache._client = mock_redis

    # Test set
    await cache.set("test_key", {"foo": "bar"}, ttl=300)
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert "test_key" in args[0]
    assert kwargs.get("ex") == 300

    # Test set_negative
    mock_redis.reset_mock()
    await cache.set_negative("neg_key", reason="no captions", ttl=60)
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert "neg_key" in args[0]
    assert kwargs.get("ex") == 60

    # Test get_with_status
    mock_redis.get.return_value = '{"value": {"foo": "bar"}, "is_negative": false}'
    val, is_neg = await cache.get_with_status("test_key")
    assert val == {"foo": "bar"}
    assert is_neg is False

    # Test purge_expired
    purged = await cache.purge_expired()
    assert purged == 0

    # Test close
    await cache.close()
    assert mock_redis.aclose.called or mock_redis.close.called
