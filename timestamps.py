from __future__ import annotations

from datetime import datetime

# Hevy has exported timestamps in more than one format over time, e.g.
# "5 Dec 2025, 11:37" (24-hour) and "Aug 31, 2026, 8:05 AM" (12-hour, AM/PM).
# Try each known format in turn.
_TIMESTAMP_FORMATS = (
    "%d %b %Y, %H:%M",
    "%b %d, %Y, %I:%M %p",
)


def format_hevy_timestamp(moment: datetime) -> str:
    """Format a naive local datetime like Hevy's 24-hour export, e.g. "5 Dec 2025, 11:37"."""
    return f"{moment.day} {moment:%b %Y, %H:%M}"


def parse_hevy_timestamp(timestamp_str: str) -> datetime:
    """Parse a Hevy export timestamp.

    Returns a naive datetime, interpreted as local time (matching how the
    string is stored by Hevy, which does not include a timezone).
    """
    value = timestamp_str.strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Invalid timestamp format: {timestamp_str}")
