import pytest
from youtube_research_mcp.utils.validation import validate_query


def test_query_length_boundary():
    """Verify maximum query length bounds (500 chars)."""
    # 500 chars is valid
    valid_query = "a" * 500
    assert validate_query(valid_query, max_length=500) == valid_query

    # 501 chars raises ValueError
    invalid_query = "a" * 501
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        validate_query(invalid_query, max_length=500)


def test_empty_query_raises():
    """Verify empty and whitespace queries are rejected."""
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        validate_query("")

    with pytest.raises(ValueError, match="empty or whitespace-only"):
        validate_query("   \n\t  ")
