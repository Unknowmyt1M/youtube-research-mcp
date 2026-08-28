import os
import re
from pathlib import Path
from typing import Optional

# YouTube 11-char alphanumeric + - + _
YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")

# URL matchers for extraction
YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})"),
]

# Sensitive token redaction regex patterns
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key
    re.compile(r"sk_[a-zA-Z0-9_-]{20,}"),  # Generic / Supadata / TranscriptAPI keys
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE),
]


def extract_video_id(input_str: str) -> str:
    """Extract and validate 11-character YouTube video ID from URL or raw ID string.

    Raises ValueError if input is invalid or cannot be parsed.
    """
    if not input_str or not isinstance(input_str, str):
        raise ValueError("Video ID or URL must be a non-empty string.")

    cleaned = input_str.strip()

    # Direct 11-char ID check
    if YOUTUBE_VIDEO_ID_PATTERN.match(cleaned):
        return cleaned

    # Check URL patterns
    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            vid = match.group(1)
            if YOUTUBE_VIDEO_ID_PATTERN.match(vid):
                return vid

    # Query param fallback parsing
    if "v=" in cleaned:
        parts = cleaned.split("v=")[1].split("&")[0].split("#")[0]
        if YOUTUBE_VIDEO_ID_PATTERN.match(parts):
            return parts

    raise ValueError(
        f"Invalid YouTube video ID or URL format: '{input_str}'. Expected 11-character ID or standard YouTube URL."
    )


def canonical_video_url(video_id: str, timestamp_seconds: Optional[int] = None) -> str:
    """Reconstruct a safe, canonical YouTube watch URL."""
    clean_id = extract_video_id(video_id)
    url = f"https://www.youtube.com/watch?v={clean_id}"
    if timestamp_seconds and timestamp_seconds > 0:
        url += f"&t={int(timestamp_seconds)}s"
    return url


def redact_secrets(text: str) -> str:
    """Redact API keys, tokens, and sensitive strings from logs or errors."""
    if not text:
        return ""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def sanitize_filename(filename: str) -> str:
    """Sanitize string for safe filesystem usage."""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)


def safe_path(base_dir: Path, filename: str) -> Path:
    """Verify resolved path stays strictly within base directory (Anti-Path Traversal)."""
    clean_name = sanitize_filename(filename)
    resolved = (base_dir / clean_name).resolve()
    base_resolved = base_dir.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"Path traversal detected for filename: {filename}")
    return resolved
