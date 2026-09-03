from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HevyWorkoutRow:
    title: str
    start_time: str
    end_time: str
    description: str
    exercise_title: str
    superset_id: Optional[str]
    exercise_notes: str
    set_index: int
    set_type: str
    weight_kg: Optional[float]
    reps: Optional[float]
    distance_km: Optional[float]
    duration_seconds: Optional[float]
    rpe: Optional[float]


@dataclass
class HevySet:
    set_index: int
    set_type: str
    weight_kg: Optional[float]
    reps: Optional[float]
    distance_km: Optional[float]
    duration_seconds: Optional[float]
    rpe: Optional[float]


@dataclass
class HevyExercise:
    exercise_title: str
    superset_id: Optional[str]
    exercise_notes: str
    sets: List[HevySet] = field(default_factory=list)


@dataclass
class HevyActivity:
    title: str
    start_time: str
    end_time: str
    description: str
    exercises: List[HevyExercise] = field(default_factory=list)
