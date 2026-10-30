from __future__ import annotations

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from models import HevyActivity
from timestamps import parse_hevy_timestamp


def state_path_for(csv_path: Path) -> Path:
    """The state file for a CSV lives next to it, named `<csv name>.hevy2fit-state.json`."""
    return csv_path.with_name(csv_path.name + ".hevy2fit-state.json")


def _canonical_key(title: str, start_time: str, end_time: str) -> str:
    """Build a state key from the parsed times, so the same workout gets the same key
    whichever of Hevy's timestamp formats it came in (24-hour, 12-hour, or the API).
    A timestamp that cannot be parsed is kept as written."""
    def canonical(timestamp: str) -> str:
        try:
            return parse_hevy_timestamp(timestamp).isoformat(timespec="minutes")
        except ValueError:
            return timestamp

    return f"{title}|{canonical(start_time)}|{canonical(end_time)}"


def activity_key(activity: HevyActivity) -> str:
    return _canonical_key(activity.title, activity.start_time, activity.end_time)


def _normalize_key(entry_key: str) -> str:
    """Convert a key from an older state file, which holds the timestamps as written in the CSV."""
    title, start_time, end_time = entry_key.rsplit("|", 2)
    return _canonical_key(title, start_time, end_time)


def _start_time_of(entry_key: str) -> datetime:
    start_time = entry_key.rsplit("|", 2)[1]
    try:
        return datetime.fromisoformat(start_time)
    except ValueError:
        return datetime.min


def _read_locked(f) -> Dict[str, dict]:
    f.seek(0)
    raw = f.read()
    if not raw.strip():
        return {}
    converted = json.loads(raw).get("converted", {})
    return {_normalize_key(key): record for key, record in converted.items()}


def _write_locked(f, converted: Dict[str, dict]) -> None:
    # Order by activity start time (oldest first), so the file reads
    # chronologically rather than in whatever order entries were added.
    ordered = dict(sorted(converted.items(), key=lambda item: _start_time_of(item[0])))
    f.seek(0)
    f.truncate()
    json.dump({"converted": ordered}, f, indent=2)
    f.write("\n")
    f.flush()


def load_state(path: Path) -> Dict[str, dict]:
    """Load the map of previously converted activities. Returns an empty map if the
    state file does not exist yet."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return _read_locked(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def find_record(state_path: Path, activity: HevyActivity) -> Optional[dict]:
    """Return the conversion record for this activity, or None if it has not been
    converted before."""
    return load_state(state_path).get(activity_key(activity))


def record_conversion(state_path: Path, activity: HevyActivity, output_path: Path) -> None:
    """Record a conversion under an exclusive lock, so two `convert` runs against the
    same CSV at the same time cannot clobber each other's entries: each run's
    read-modify-write of the whole file happens atomically while holding the lock."""
    state_path.touch(exist_ok=True)
    with open(state_path, "r+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            converted = _read_locked(f)
            converted[activity_key(activity)] = {
                "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "output": str(output_path),
            }
            _write_locked(f, converted)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
