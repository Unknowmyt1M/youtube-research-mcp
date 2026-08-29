import pytest
from youtube_research_mcp.utils.validation import validate_language_code


def test_valid_language_codes():
    """Verify ISO 639 and BCP 47 codes pass validation."""
    assert validate_language_code("en") == "en"
    assert validate_language_code("hi") == "hi"
    assert validate_language_code("es") == "es"
    assert validate_language_code("fr") == "fr"
    assert validate_language_code("en-US") == "en-US"
    assert validate_language_code("zh-Hans") == "zh-Hans"
    assert validate_language_code("es-419") == "es-419"
    assert validate_language_code("en-orig") == "en"  # Strips internal yt-dlp orig


def test_empty_and_default_language_codes():
    """Empty or None strings should return default."""
    assert validate_language_code(None, default="en") == "en"
    assert validate_language_code("", default="en") == "en"
    assert validate_language_code("   ", default="en") == "en"
    assert validate_language_code(None, allow_none=True) is None


def test_invalid_language_codes_raise():
    """Invalid symbols and non-standard identifiers should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid language code"):
        validate_language_code("$$$")

    with pytest.raises(ValueError, match="Invalid language code"):
        validate_language_code("12345")

    with pytest.raises(ValueError, match="Invalid language code"):
        validate_language_code("<script>")
