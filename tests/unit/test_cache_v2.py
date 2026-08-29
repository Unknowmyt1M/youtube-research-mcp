import asyncio
import os
import tempfile
import pytest

from youtube_research_mcp.cache.sqlite import SQLiteCache


@pytest.mark.asyncio
async def test_cache_versioning_and_negative_caching():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    try:
        cache = SQLiteCache(db_path=temp_db)

        # 1. Test standard set and versioned key formatting
        assert cache.format_key("search:query").startswith("v2:search:query")
        await cache.set("test_key", {"data": "hello"}, ttl=60)

        val, is_neg = await cache.get_with_status("test_key")
        assert is_neg is False
        assert val == {"data": "hello"}

        # 2. Test negative caching
        await cache.set_negative("uncaptioned_video", reason="No captions available", ttl=60)

        neg_val, is_neg2 = await cache.get_with_status("uncaptioned_video")
        assert is_neg2 is True
        assert neg_val is not None
        assert neg_val.get("__negative__") is True

        # Standard get() should return None for negative cache
        assert await cache.get("uncaptioned_video") is None

        # 3. Test purge_expired
        await cache.set("short_lived", {"data": "bye"}, ttl=0)  # Expires immediately
        await asyncio.sleep(0.05)

        purged_count = await cache.purge_expired()
        assert purged_count >= 1

    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)
