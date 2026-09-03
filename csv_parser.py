from __future__ import annotations

import csv
from io import StringIO
from typing import List, Optional

from models import HevyWorkoutRow

_NUMERIC_FIELDS = ("weight_kg", "reps", "distance_km", "duration_seconds", "rpe")


def _to_float(value: Optional[str]) -> Optional[float]:
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: Optional[str]) -> int:
    value = (value or "").strip()
    if value == "":
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def parse_hevy_csv(csv_content: str) -> List[HevyWorkoutRow]:
    """Parse a Hevy workout export CSV into flat per-set rows."""
    reader = csv.DictReader(StringIO(csv_content))
    rows: List[HevyWorkoutRow] = []

    for raw in reader:
        record = {(key or "").strip(): (value or "") for key, value in raw.items() if key}

        if not any(v.strip() for v in record.values()):
            continue

        superset_id = record.get("superset_id", "").strip() or None

        rows.append(HevyWorkoutRow(
            title=record.get("title", "").strip(),
            start_time=record.get("start_time", "").strip(),
            end_time=record.get("end_time", "").strip(),
            description=record.get("description", "").strip(),
            exercise_title=record.get("exercise_title", "").strip(),
            superset_id=superset_id,
            exercise_notes=record.get("exercise_notes", "").strip(),
            set_index=_to_int(record.get("set_index")),
            set_type=record.get("set_type", "").strip(),
            weight_kg=_to_float(record.get("weight_kg")),
            reps=_to_float(record.get("reps")),
            distance_km=_to_float(record.get("distance_km")),
            duration_seconds=_to_float(record.get("duration_seconds")),
            rpe=_to_float(record.get("rpe")),
        ))

    return rows
