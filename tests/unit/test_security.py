import pytest
from youtube_research_mcp.utils.security import (
    canonical_video_url,
    extract_video_id,
    redact_secrets,
)


def test_extract_valid_11_char_id():
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert extract_video_id("_a1b2C3-d4E") == "_a1b2C3-d4E"


def test_extract_from_various_youtube_urls():
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ&feature=shared",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=120",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ?si=abcdef",
    ]
    for url in urls:
        assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_invalid_input_raises():
    with pytest.raises(ValueError):
        extract_video_id("")
    with pytest.raises(ValueError):
        extract_video_id("http://attacker.com/malicious")
    with pytest.raises(ValueError):
        extract_video_id("short_id")
    with pytest.raises(ValueError):
        extract_video_id("way_too_long_video_id_to_be_valid_123456")


def test_canonical_video_url():
    assert (
        canonical_video_url("dQw4w9WgXcQ")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert (
        canonical_video_url("dQw4w9WgXcQ", 145)
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=145s"
    )


def test_redact_secrets():
    text = "Key is AIzaSyAO_FJ2SlqaeukAMQIqYGcxErWqvDAGBpQ and sk_live_12345678901234567890"
    redacted = redact_secrets(text)
    assert "AIzaSy" not in redacted
    assert "sk_live" not in redacted
    assert "[REDACTED_SECRET]" in redacted
