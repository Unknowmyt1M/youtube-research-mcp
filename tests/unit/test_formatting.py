from youtube_research_mcp.utils.formatting import (
    format_duration,
    format_timestamp,
    make_timestamp_url,
    parse_timestamp,
)


def test_format_timestamp():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(45) == "00:45"
    assert format_timestamp(75) == "01:15"
    assert format_timestamp(3665) == "01:01:05"


def test_parse_timestamp():
    assert parse_timestamp("01:15") == 75.0
    assert parse_timestamp("01:01:05") == 3665.0
    assert parse_timestamp("45") == 45.0
    assert parse_timestamp("") == 0.0


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3665) == "1h 1m 5s"
    assert format_duration(None) == "Unknown duration"


def test_make_timestamp_url():
    assert (
        make_timestamp_url("dQw4w9WgXcQ", 124.5)
        == "https://youtu.be/dQw4w9WgXcQ?t=124"
    )
    assert (
        make_timestamp_url("dQw4w9WgXcQ", 0)
        == "https://youtu.be/dQw4w9WgXcQ?t=0"
    )
