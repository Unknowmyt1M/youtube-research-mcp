import pytest
from youtube_research_mcp.providers.innertube import InnerTubeProvider


def test_innertube_published_time_parsing():
    """Verify InnerTubeProvider extracts published_time correctly."""
    provider = InnerTubeProvider()
    mock_data = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {
                    "sectionListRenderer": {
                        "contents": [
                            {
                                "itemSectionRenderer": {
                                    "contents": [
                                        {
                                            "videoRenderer": {
                                                "videoId": "abc12345678",
                                                "title": {"runs": [{"text": "Test Video"}]},
                                                "ownerText": {"runs": [{"text": "Test Channel"}]},
                                                "publishedTimeText": {"simpleText": "3 days ago"},
                                                "lengthText": {"simpleText": "10:00"},
                                                "viewCountText": {"simpleText": "1,200 views"},
                                            }
                                        },
                                        {
                                            "videoRenderer": {
                                                "videoId": "xyz87654321",
                                                "title": {"runs": [{"text": "Runs Time Video"}]},
                                                "ownerText": {"runs": [{"text": "Runs Channel"}]},
                                                "publishedTimeText": {"runs": [{"text": "2 years ago"}]},
                                                "lengthText": {"simpleText": "05:00"},
                                            }
                                        },
                                        {
                                            "videoRenderer": {
                                                "videoId": "non12345678",
                                                "title": {"runs": [{"text": "No Time Video"}]},
                                                "ownerText": {"runs": [{"text": "No Time Channel"}]},
                                                # missing publishedTimeText
                                                "lengthText": {"simpleText": "01:00"},
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }
    }

    results = provider._parse_search_response(mock_data, max_results=5)
    assert len(results) == 3

    assert results[0].video_id == "abc12345678"
    assert results[0].published_time == "3 days ago"

    assert results[1].video_id == "xyz87654321"
    assert results[1].published_time == "2 years ago"

    assert results[2].video_id == "non12345678"
    assert results[2].published_time is None
