from __future__ import annotations

from collections import OrderedDict
from typing import List, Optional

from models import HevyActivity, HevyExercise, HevySet, HevyWorkoutRow
from timestamps import parse_hevy_timestamp


def group_rows_by_activity(rows: List[HevyWorkoutRow]) -> List[HevyActivity]:
    """Group flat CSV rows into activities (by title + start_time + end_time), each with
    its exercises and sets, mirroring how Hevy exports a workout across many rows."""
    grouped: "OrderedDict[tuple, List[HevyWorkoutRow]]" = OrderedDict()
    for row in rows:
        key = (row.title, row.start_time, row.end_time)
        grouped.setdefault(key, []).append(row)

    activities: List[HevyActivity] = []
    for (title, start_time, end_time), group_rows in grouped.items():
        description = group_rows[0].description if group_rows else ""

        exercise_sets: "OrderedDict[str, List[HevySet]]" = OrderedDict()
        for row in group_rows:
            exercise_sets.setdefault(row.exercise_title, []).append(HevySet(
                set_index=row.set_index,
                set_type=row.set_type,
                weight_kg=row.weight_kg,
                reps=row.reps,
                distance_km=row.distance_km,
                duration_seconds=row.duration_seconds,
                rpe=row.rpe,
            ))

        exercises: List[HevyExercise] = []
        for exercise_title, sets in exercise_sets.items():
            first_row = next(r for r in group_rows if r.exercise_title == exercise_title)
            exercises.append(HevyExercise(
                exercise_title=exercise_title,
                superset_id=first_row.superset_id,
                exercise_notes=first_row.exercise_notes,
                sets=sorted(sets, key=lambda s: s.set_index),
            ))

        activities.append(HevyActivity(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            exercises=exercises,
        ))

    return activities


def order_activities(activities: List[HevyActivity]) -> List[HevyActivity]:
    """Order activities chronologically (oldest first, most recent last)."""
    return sorted(
        activities,
        key=lambda a: (parse_hevy_timestamp(a.end_time), parse_hevy_timestamp(a.start_time)),
    )


def select_activity(activities: List[HevyActivity], index: int = -1) -> Optional[HevyActivity]:
    """Pick one activity, ordered chronologically. Default index -1 is the most recent
    activity, matching the "process the last activity" behavior of the original app."""
    if not activities:
        return None

    ordered = order_activities(activities)
    try:
        return ordered[index]
    except IndexError:
        return None
