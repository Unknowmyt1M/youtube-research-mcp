from datetime import datetime, timedelta
import pytest

from youtube_research_mcp.models.search import VideoSearchResult
from youtube_research_mcp.services.search import SearchService


def test_search_service_date_post_filtering():
    service = SearchService()

    # Create dummy results with different published strings
    results = [
        VideoSearchResult(
            video_id="vid11111111",
            title="Video 2026",
            channel="Tech Channel",
            published_time="2 days ago",
            url="https://youtu.be/vid11111111",
        ),
        VideoSearchResult(
            video_id="vid22222222",
            title="Video 2024",
            channel="Old Channel",
            published_time="2 years ago",
            url="https://youtu.be/vid22222222",
        ),
        VideoSearchResult(
            video_id="vid33333333",
            title="Video 2025",
            channel="Mid Channel",
            published_time="6 months ago",
            url="https://youtu.be/vid33333333",
        ),
    ]

    # Filter published_after: 30 days ago
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    filtered = service._apply_post_filters(
        results, published_after=thirty_days_ago, published_before=None
    )

    assert len(filtered) == 1
    assert filtered[0].video_id == "vid11111111"

    # Filter published_before: 1 year ago
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    filtered_old = service._apply_post_filters(
        results, published_after=None, published_before=one_year_ago
    )

    assert len(filtered_old) == 1
    assert filtered_old[0].video_id == "vid22222222"
