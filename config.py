from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_LBS_TO_KG = 0.453592

DEFAULT_WEIGHT = 70.0
DEFAULT_UNIT = "kg"
DEFAULT_MET_VALUE = 5.0
DEFAULT_REST_TIME = 60
DEFAULT_EXERCISE_TIME = 60


@dataclass
class Config:
    weight: float = DEFAULT_WEIGHT
    unit: str = DEFAULT_UNIT
    met_value: float = DEFAULT_MET_VALUE
    rest_time: int = DEFAULT_REST_TIME
    exercise_time: int = DEFAULT_EXERCISE_TIME


def load_config(path: Optional[Path]) -> Config:
    """Load weight/unit/metValue/restTime/exerciseTime from a JSON file, falling back
    to defaults for missing or invalid fields. Returns defaults if path is None."""
    config = Config()
    if path is None:
        return config

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data.get("weight"), (int, float)) and data["weight"] > 0:
        config.weight = float(data["weight"])
    if data.get("unit") in ("kg", "lbs"):
        config.unit = data["unit"]
    if isinstance(data.get("metValue"), (int, float)) and data["metValue"] > 0:
        config.met_value = float(data["metValue"])
    if isinstance(data.get("restTime"), (int, float)) and data["restTime"] >= 0:
        config.rest_time = int(data["restTime"])
    if isinstance(data.get("exerciseTime"), (int, float)) and data["exerciseTime"] > 0:
        config.exercise_time = int(data["exerciseTime"])

    return config


def convert_weight_to_kg(weight: float, unit: str) -> float:
    if unit == "lbs":
        return weight * _LBS_TO_KG
    return weight
