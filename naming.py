from __future__ import annotations

import re

from models import HevyActivity
from timestamps import parse_hevy_timestamp

_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9]+")


def slugify(text: str) -> str:
    """Reduce text to a filesystem-safe slug: letters, digits, and underscores."""
    slug = _UNSAFE_CHARS_RE.sub("_", text).strip("_")
    return slug or "workout"


def filename_for_activity(activity: HevyActivity, extension: str = ".fit") -> str:
    """Build an output filename from an activity's start time and title, e.g.
    "20260831-0655_Upper_A.fit"."""
    start = parse_hevy_timestamp(activity.start_time)
    return f"{start.strftime('%Y%m%d-%H%M')}_{slugify(activity.title)}{extension}"
