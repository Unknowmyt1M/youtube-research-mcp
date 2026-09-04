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


def validate_translation_content(text: str, target_lang: str) -> bool:
    """Verify that transcript text actually contains the target language script / characters."""
    if not text or not text.strip():
        return False

    base_target = target_lang.lower().split("-")[0]
    
    # Devanagari (Hindi)
    if base_target in ("hi", "mr", "ne"):
        devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
        return devanagari_count > 0

    # CJK (Chinese, Japanese)
    if base_target in ("zh", "ja"):
        cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]", text))
        return cjk_count > 0

    # Korean Hangul
    if base_target == "ko":
        hangul_count = len(re.findall(r"[\uac00-\ud7af\u1100-\u11ff]", text))
        return hangul_count > 0

    # Arabic / Persian / Urdu
    if base_target in ("ar", "fa", "ur"):
        arabic_count = len(re.findall(r"[\u0600-\u06FF]", text))
        return arabic_count > 0

    # Cyrillic (Russian, Ukrainian)
    if base_target in ("ru", "uk", "bg"):
        cyrillic_count = len(re.findall(r"[\u0400-\u04FF]", text))
        return cyrillic_count > 0

    # Default for Latin scripts: ensure non-empty text
    return len(text.strip()) > 0

