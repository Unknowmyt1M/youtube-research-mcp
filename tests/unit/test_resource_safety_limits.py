import asyncio
import tempfile
import time
from unittest.mock import AsyncMock, patch
import pytest

from youtube_research_mcp.cache.sqlite import SQLiteCache
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import TranscriptResult, TranscriptSegment
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.providers.ytdlp_provider import YtDlpProvider
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.utils.formatting import format_timestamp, make_timestamp_url
from youtube_research_mcp.utils.validation import validate_query


@pytest.mark.asyncio
async def test_res001_transcript_segment_limit_enforcement():
    """RES-001: Test transcript segment limits (at limit, limit + 1, and large simulated)."""
    service = TranscriptService()
    test_limit = 50

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "MAX_TRANSCRIPT_SEGMENTS", test_limit)

        def make_segment(i: int, vid: str = "dQw4w9WgXcQ") -> TranscriptSegment:
            return TranscriptSegment(
                start=float(i),
                duration=1.0,
                end=float(i + 1),
                text=f"word{i}",
                timestamp_formatted=format_timestamp(float(i)),
                url=make_timestamp_url(vid, float(i)),
            )

        # 1. Exactly at limit (50 segments)
        vid_exact = "dQw4w9WgXc1"
        exact_segments = [make_segment(i, vid_exact) for i in range(test_limit)]
        exact_result = TranscriptResult(
            video_id=vid_exact,
            language="en",
            requested_language="en",
            actual_language="en",
            is_generated=False,
            is_translated=False,
            total_segments=len(exact_segments),
            total_words=len(exact_segments),
            duration_seconds=50.0,
            segments=exact_segments,
            full_text=" ".join(s.text for s in exact_segments),
        )

        with patch.object(service.router, "get_transcript", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = exact_result
            res = await service.get_transcript(vid_exact, language="en")
            assert res is not None
            assert len(res.segments) == test_limit
            assert res.total_segments == test_limit

        # 2. Limit + 1 (51 segments -> truncated to 50)
        vid_over = "dQw4w9WgXc2"
        over_segments = [make_segment(i, vid_over) for i in range(test_limit + 1)]
        over_result = TranscriptResult(
            video_id=vid_over,
            language="en",
            requested_language="en",
            actual_language="en",
            is_generated=False,
            is_translated=False,
            total_segments=len(over_segments),
            total_words=len(over_segments),
            duration_seconds=51.0,
            segments=over_segments,
            full_text=" ".join(s.text for s in over_segments),
        )

        with patch.object(service.router, "get_transcript", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = over_result
            res = await service.get_transcript(vid_over, language="en")
            assert res is not None
            assert len(res.segments) == test_limit
            assert res.total_segments == test_limit
            assert res.duration_seconds == float(test_limit)
            assert res.segments[-1].text == f"word{test_limit - 1}"

        # 3. Large simulated transcript (500 segments -> truncated to 50)
        vid_large = "dQw4w9WgXc3"
        large_segments = [make_segment(i, vid_large) for i in range(500)]
        large_result = TranscriptResult(
            video_id=vid_large,
            language="en",
            requested_language="en",
            actual_language="en",
            is_generated=False,
            is_translated=False,
            total_segments=500,
            total_words=500,
            duration_seconds=500.0,
            segments=large_segments,
            full_text=" ".join(s.text for s in large_segments),
        )

        with patch.object(service.router, "get_transcript", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = large_result
            res = await service.get_transcript(vid_large, language="en")
            assert res is not None
            assert len(res.segments) == test_limit
            assert res.total_segments == test_limit
            assert res.duration_seconds == float(test_limit)


def test_res001_provider_json3_early_break():
    """RES-001: Test provider json3 parsing stops early when reaching MAX_TRANSCRIPT_SEGMENTS."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "MAX_TRANSCRIPT_SEGMENTS", 10)

        raw_events = [
            {
                "tStartMs": i * 1000,
                "dDurationMs": 1000,
                "segs": [{"utf8": f"seg_{i}", "tOffsetMs": 0}],
            }
            for i in range(50)
        ]
        json3_data = {"events": raw_events}

        # InnerTube parsing
        inner_provider = InnerTubeProvider()
        inner_segs = inner_provider._parse_json3_timedtext(json3_data, "dQw4w9WgXcQ")
        assert len(inner_segs) == 10

        # YtDlp parsing
        ytdlp_provider = YtDlpProvider()
        ytdlp_segs = ytdlp_provider._parse_json3(json3_data, "dQw4w9WgXcQ")
        assert len(ytdlp_segs) == 10


@pytest.mark.asyncio
async def test_res002_sqlite_cache_pruning_and_namespace_isolation():
    """RES-002: Test SQLite cache growth pruning at MAX_CACHE_ENTRIES and namespace isolation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    cache = SQLiteCache(db_path)
    limit = 20

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "MAX_CACHE_ENTRIES", limit)

        # 1. Fill cache below limit
        for i in range(15):
            await cache.set(f"item_{i}", {"val": i}, ttl=3600)

        # 2. Add foreign namespace item directly to SQLite
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO cache_store (key, value, is_negative, created_at, expires_at) VALUES ('v1:legacy_key', '\"keep\"', 0, 0, 9999999999);"
            )
            await db.commit()

        # 3. Add expired entries
        now = time.time()
        async with aiosqlite.connect(db_path) as db:
            for exp_i in range(5):
                await db.execute(
                    "INSERT INTO cache_store (key, value, is_negative, created_at, expires_at) VALUES (?, '\"exp\"', 0, ?, ?);",
                    (f"v2:expired_{exp_i}", now - 100, now - 10),
                )
            await db.commit()

        # 4. Trigger pruning by inserting more items
        for i in range(15, 25):
            await cache.set(f"item_{i}", {"val": i}, ttl=3600)

        # 5. Verify total active items in v2 namespace do not exceed limit + grace batch
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM cache_store WHERE key LIKE 'v2:%';") as cur:
                v2_count = (await cur.fetchone())[0]
                assert v2_count <= limit + 5

            # Foreign namespace key must survive
            async with db.execute("SELECT value FROM cache_store WHERE key = 'v1:legacy_key';") as cur:
                row = await cur.fetchone()
                assert row is not None
                assert row[0] == '"keep"'

        # 6. Test clear() only clears current namespace (v2)
        await cache.clear()
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM cache_store WHERE key LIKE 'v2:%';") as cur:
                v2_cleared = (await cur.fetchone())[0]
                assert v2_cleared == 0

            async with db.execute("SELECT value FROM cache_store WHERE key = 'v1:legacy_key';") as cur:
                row = await cur.fetchone()
                assert row is not None
                assert row[0] == '"keep"'


@pytest.mark.asyncio
async def test_res003_query_length_boundary_across_services():
    """RES-003: Test query length boundaries across search, find_in_video, and research services."""
    max_len = settings.MAX_QUERY_LENGTH  # 500 chars

    # 1. Valid at boundary
    valid_query = "a" * max_len
    assert validate_query(valid_query, max_length=max_len) == valid_query

    # 2. Invalid beyond boundary
    oversized = "a" * (max_len + 1)
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        validate_query(oversized, max_length=max_len)

    # 3. Empty query
    with pytest.raises(ValueError, match="must not be empty"):
        validate_query("", max_length=max_len)
    with pytest.raises(ValueError, match="must not be empty"):
        validate_query("   ", max_length=max_len)
