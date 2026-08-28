import math
from typing import Optional


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS human-readable timecode."""
    if seconds is None or math.isnan(seconds) or seconds < 0:
        return "00:00"

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_timestamp(time_str: str) -> float:
    """Parse HH:MM:SS or MM:SS timecode or numeric seconds string into float seconds."""
    if not time_str:
        return 0.0

    time_str = time_str.strip()
    # If pure number
    try:
        return float(time_str)
    except ValueError:
        pass

    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except (ValueError, TypeError):
        pass

    return 0.0


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds into human-readable representation."""
    if not seconds or seconds <= 0:
        return "Unknown duration"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def make_timestamp_url(video_id: str, start_seconds: float) -> str:
    """Construct deep-link YouTube URL with exact integer timestamp."""
    secs = max(0, int(start_seconds))
    return f"https://youtu.be/{video_id}?t={secs}"
