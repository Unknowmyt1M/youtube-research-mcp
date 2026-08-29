import re
from typing import Any, Optional
from youtube_research_mcp.config import settings
from youtube_research_mcp.models.research import ResearchDepth

# BCP 47 / ISO 639 standard language tag validator (e.g. en, en-US, hi, es-419, zh-Hans, etc.)
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$")

# ISO 8601 Date regex YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_query(
    query: Any,
    max_length: Optional[int] = None,
    field_name: str = "query",
) -> str:
    """Validate non-empty search/research query with bounded character length."""
    limit = max_length if max_length is not None else settings.MAX_QUERY_LENGTH
    if query is None or not isinstance(query, str):
        raise ValueError(f"'{field_name}' must be a non-empty string.")

    cleaned = query.strip()
    if not cleaned:
        raise ValueError(f"'{field_name}' must not be empty or whitespace-only.")

    if len(cleaned) > limit:
        raise ValueError(
            f"'{field_name}' exceeds maximum allowed length of {limit} characters (received {len(cleaned)})."
        )

    return cleaned


def validate_language_code(
    lang: Optional[str],
    default: Optional[str] = "en",
    allow_none: bool = False,
) -> Optional[str]:
    """Validate and normalize BCP 47 / ISO 639 language code."""
    if lang is None:
        return None if allow_none else default

    if not isinstance(lang, str):
        raise ValueError("Language code must be a string.")

    cleaned = lang.strip()
    if not cleaned:
        return None if allow_none else default

    # Strip internal yt-dlp -orig suffix if present
    norm_tag = cleaned.replace("-orig", "")

    if not LANGUAGE_CODE_PATTERN.match(norm_tag):
        raise ValueError(
            f"Invalid language code: '{lang}'. Expected standard ISO 639 / BCP 47 code (e.g. 'en', 'hi', 'es', 'zh-Hans')."
        )

    return norm_tag.lower() if "-" not in norm_tag else norm_tag


def validate_date_filter(date_str: Optional[str]) -> Optional[str]:
    """Validate ISO date string YYYY-MM-DD."""
    if date_str is None:
        return None

    if not isinstance(date_str, str):
        raise ValueError("Date filter must be a string.")

    cleaned = date_str.strip()
    if not cleaned:
        return None

    if not DATE_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid date format: '{date_str}'. Expected ISO format 'YYYY-MM-DD' (e.g. '2026-01-15')."
        )

    return cleaned


def validate_max_results(
    val: Any, min_val: int = 1, max_val: int = 25, default: int = 5
) -> int:
    """Validate bounded integer result limit."""
    if val is None:
        return default
    try:
        num = int(val)
    except (TypeError, ValueError):
        raise ValueError(f"max_results must be an integer between {min_val} and {max_val}.")

    if num < min_val or num > max_val:
        raise ValueError(
            f"max_results must be between {min_val} and {max_val} (received {num})."
        )
    return num
