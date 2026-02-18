"""Shared utility helpers for CTK."""

import re


def compact_duration(duration: str) -> str:
    """Compact duration strings to minimal format.

    Converts verbose durations to compact form:
        "2 hours" -> "2h"
        "3 days ago" -> "3d"
        "30 minutes" -> "30m"

    Args:
        duration: Duration string to compact

    Returns:
        Compacted duration string
    """
    if not duration:
        return duration

    # Pattern list: (regex_pattern, replacement)
    patterns = [
        (r"(\d+)\s*weeks?", r"\1w"),
        (r"(\d+)\s*days?", r"\1d"),
        (r"(\d+)\s*(?:hours?|hrs?)", r"\1h"),
        (r"(\d+)\s*(?:minutes?|mins?)", r"\1m"),
        (r"(\d+)\s*(?:seconds?|secs?)", r"\1s"),
    ]

    for pattern, replacement in patterns:
        duration = re.sub(pattern, replacement, duration, flags=re.IGNORECASE)

    # Remove parenthetical info (e.g., "(healthy)", "(0)")
    duration = re.sub(r"\s*\(.*?\)", "", duration)

    # Remove "ago" suffix
    duration = duration.replace(" ago", "")

    return duration.strip()
