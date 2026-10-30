from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from datetime import datetime
from io import StringIO
from typing import Any, Dict, Iterator, List, Optional

from timestamps import format_hevy_timestamp

API_BASE_URL = "https://api.hevyapp.com"
PAGE_SIZE = 10  # the API rejects larger pages
REQUEST_TIMEOUT_SECONDS = 30

CSV_COLUMNS = (
    "title", "start_time", "end_time", "description", "exercise_title", "superset_id",
    "exercise_notes", "set_index", "set_type", "weight_kg", "reps", "distance_km",
    "duration_seconds", "rpe",
)


class HevyApiError(Exception):
    pass


def _get_json(path: str, api_key: str, params: Dict[str, Any]) -> dict:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}?{query}",
        headers={"api-key": api_key, "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise HevyApiError(
                "Hevy rejected the API key (HTTP %d). The API requires a Hevy PRO account; "
                "get your key at https://hevy.com/settings?developer" % e.code
            ) from e
        raise HevyApiError(f"Hevy API request failed: HTTP {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise HevyApiError(f"could not reach the Hevy API: {e.reason}") from e


def fetch_workouts(api_key: str) -> Iterator[dict]:
    """Yield every workout on the account, newest first, following the pagination."""
    page = 1
    while True:
        data = _get_json("/v1/workouts", api_key, {"page": page, "pageSize": PAGE_SIZE})
        yield from data.get("workouts", [])
        if page >= data.get("page_count", 0):
            return
        page += 1


def _to_local_timestamp(iso_timestamp: str) -> str:
    # fromisoformat() only accepts a trailing "Z" from Python 3.11 on.
    moment = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    # The CSV export carries naive local times, so convert to match it.
    return format_hevy_timestamp(moment.astimezone().replace(tzinfo=None))


def _blank_if_none(value: Optional[Any]) -> Any:
    return "" if value is None else value


def workouts_to_csv(workouts: List[dict]) -> str:
    """Render API workouts as a Hevy CSV export: one row per set, same columns."""
    out = StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)

    for workout in workouts:
        start_time = _to_local_timestamp(workout["start_time"])
        end_time = _to_local_timestamp(workout["end_time"])
        for exercise in workout.get("exercises", []):
            for set_ in exercise.get("sets", []):
                distance_meters = set_.get("distance_meters")
                writer.writerow([
                    workout.get("title") or "",
                    start_time,
                    end_time,
                    workout.get("description") or "",
                    exercise.get("title") or "",
                    _blank_if_none(exercise.get("superset_id")),
                    exercise.get("notes") or "",
                    set_.get("index", 0),
                    set_.get("type") or "",
                    _blank_if_none(set_.get("weight_kg")),
                    _blank_if_none(set_.get("reps")),
                    "" if distance_meters is None else distance_meters / 1000,
                    _blank_if_none(set_.get("duration_seconds")),
                    _blank_if_none(set_.get("rpe")),
                ])

    return out.getvalue()
