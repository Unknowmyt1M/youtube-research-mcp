import asyncio
import os
import tempfile
import pytest
from youtube_research_mcp.cache.sqlite import SQLiteCache


@pytest.mark.asyncio
async def test_sqlite_cache_set_get_and_expiration():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        cache = SQLiteCache(db_path)

        # Test set and get
        test_payload = {"video_id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up"}
        await cache.set("test_key", test_payload, ttl_seconds=10)

        result = await cache.get("test_key")
        assert result is not None
        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["title"] == "Never Gonna Give You Up"

        # Test miss
        miss = await cache.get("non_existent_key")
        assert miss is None

        # Test expiration
        await cache.set("expired_key", {"expired": True}, ttl_seconds=-5)
        expired_res = await cache.get("expired_key")
        assert expired_res is None

        # Test delete
        deleted = await cache.delete("test_key")
        assert deleted is True
        assert await cache.get("test_key") is None

        await cache.close()
