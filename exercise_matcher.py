from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_LOOKUP_TABLE_PATH = Path(__file__).parent / "data" / "exercise-lookup-table.json"


@dataclass
class ExerciseMatch:
    category: int
    category_subtype: int
    confidence: float


# Fallback keyword mappings, used only when the lookup table has no match.
# Mirrors the HEVY -> Garmin FIT category/subtype mappings from the original app.
_KEYWORD_MAPPINGS: List[Dict[str, Any]] = [
    {"keywords": ["bench press", "chest press"], "category": 0, "category_subtype": 1},
    {"keywords": ["dumbbell bench", "db bench"], "category": 0, "category_subtype": 6},
    {"keywords": ["incline bench"], "category": 0, "category_subtype": 8},
    {"keywords": ["incline dumbbell"], "category": 0, "category_subtype": 9},

    {"keywords": ["squat"], "category": 28, "category_subtype": 61},
    {"keywords": ["back squat", "barbell squat"], "category": 28, "category_subtype": 6},
    {"keywords": ["front squat"], "category": 28, "category_subtype": 8},
    {"keywords": ["goblet squat"], "category": 28, "category_subtype": 37},
    {"keywords": ["leg press"], "category": 28, "category_subtype": 0},

    {"keywords": ["deadlift"], "category": 8, "category_subtype": 0},
    {"keywords": ["romanian deadlift", "rdl"], "category": 8, "category_subtype": 23},
    {"keywords": ["sumo deadlift"], "category": 8, "category_subtype": 15},
    {"keywords": ["trap bar deadlift"], "category": 8, "category_subtype": 17},

    {"keywords": ["pull up", "pullup"], "category": 21, "category_subtype": 38},
    {"keywords": ["chin up", "chinup"], "category": 21, "category_subtype": 39},
    {"keywords": ["lat pulldown", "lat pull"], "category": 21, "category_subtype": 13},
    {"keywords": ["wide grip pull"], "category": 21, "category_subtype": 26},

    {"keywords": ["barbell row", "bent over row"], "category": 23, "category_subtype": 0},
    {"keywords": ["dumbbell row", "db row"], "category": 23, "category_subtype": 1},
    {"keywords": ["cable row"], "category": 23, "category_subtype": 2},
    {"keywords": ["t-bar row"], "category": 23, "category_subtype": 3},
    {"keywords": ["seated row"], "category": 23, "category_subtype": 4},

    {"keywords": ["shoulder press", "overhead press"], "category": 24, "category_subtype": 0},
    {"keywords": ["dumbbell shoulder", "db shoulder"], "category": 24, "category_subtype": 1},
    {"keywords": ["military press"], "category": 24, "category_subtype": 2},
    {"keywords": ["barbell shoulder"], "category": 24, "category_subtype": 3},

    {"keywords": ["bicep curl", "biceps curl"], "category": 7, "category_subtype": 0},
    {"keywords": ["barbell curl"], "category": 7, "category_subtype": 1},
    {"keywords": ["dumbbell curl", "db curl"], "category": 7, "category_subtype": 2},
    {"keywords": ["hammer curl"], "category": 7, "category_subtype": 3},
    {"keywords": ["cable curl"], "category": 7, "category_subtype": 4},

    {"keywords": ["tricep extension", "triceps extension"], "category": 30, "category_subtype": 0},
    {"keywords": ["tricep pushdown", "triceps pushdown"], "category": 30, "category_subtype": 1},
    {"keywords": ["overhead tricep", "overhead triceps"], "category": 30, "category_subtype": 2},
    {"keywords": ["close grip bench"], "category": 30, "category_subtype": 3},

    {"keywords": ["push up", "pushup"], "category": 22, "category_subtype": 0},
    {"keywords": ["incline push"], "category": 22, "category_subtype": 1},
    {"keywords": ["decline push"], "category": 22, "category_subtype": 2},

    {"keywords": ["lunge"], "category": 17, "category_subtype": 0},
    {"keywords": ["walking lunge"], "category": 17, "category_subtype": 1},
    {"keywords": ["reverse lunge"], "category": 17, "category_subtype": 2},
    {"keywords": ["split squat"], "category": 17, "category_subtype": 3},

    {"keywords": ["leg curl"], "category": 15, "category_subtype": 0},
    {"keywords": ["lying leg curl"], "category": 15, "category_subtype": 1},
    {"keywords": ["seated leg curl"], "category": 15, "category_subtype": 2},

    {"keywords": ["calf raise"], "category": 1, "category_subtype": 18},
    {"keywords": ["seated calf"], "category": 1, "category_subtype": 6},

    {"keywords": ["plank"], "category": 19, "category_subtype": 0},
    {"keywords": ["sit up"], "category": 27, "category_subtype": 0},
    {"keywords": ["crunch"], "category": 6, "category_subtype": 0},
    {"keywords": ["russian twist"], "category": 5, "category_subtype": 46},

    {"keywords": ["hip raise", "hip thrust"], "category": 10, "category_subtype": 0},
    {"keywords": ["glute bridge"], "category": 10, "category_subtype": 11},

    {"keywords": ["shrug"], "category": 26, "category_subtype": 0},
    {"keywords": ["dumbbell shrug"], "category": 26, "category_subtype": 1},

    {"keywords": ["lateral raise"], "category": 14, "category_subtype": 0},
    {"keywords": ["side raise"], "category": 14, "category_subtype": 1},

    {"keywords": ["fly", "flye"], "category": 9, "category_subtype": 2},
    {"keywords": ["pec fly"], "category": 9, "category_subtype": 0},

    {"keywords": ["burpee"], "category": 29, "category_subtype": 0},
]

_TOTAL_BODY_FALLBACK = ExerciseMatch(category=29, category_subtype=0, confidence=0.3)


def load_lookup_table(path: Path = DEFAULT_LOOKUP_TABLE_PATH) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_exercise_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def calculate_similarity(str1: str, str2: str) -> float:
    s1 = normalize_exercise_name(str1)
    s2 = normalize_exercise_name(str2)

    if s1 == s2:
        return 1.0

    if s1 in s2 or s2 in s1:
        return 0.8

    words1 = s1.split(" ")
    words2 = s2.split(" ")
    common_words = [w for w in words1 if w in words2]
    if common_words:
        return 0.5 + (len(common_words) / max(len(words1), len(words2))) * 0.3

    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0.0

    min_len = min(len(s1), len(s2))
    matches = sum(1 for i in range(min_len) if s1[i] == s2[i])
    return matches / max_len * 0.5


def find_exercise_match(hevy_exercise_name: str, lookup_table: List[Dict[str, Any]]) -> ExerciseMatch:
    """Find the best matching FIT exercise category/subtype for a HEVY exercise name.

    First checks the lookup table for exact/fuzzy matches, then falls back to keyword
    matching, then fuzzy matching against Garmin exercise names, then "Total Body"."""
    normalized = normalize_exercise_name(hevy_exercise_name)

    # Step 1: exact match against lookup table hevy titles
    for entry in lookup_table:
        hevy_title = entry.get("hevy", {}).get("exerciseTitle")
        if hevy_title and normalize_exercise_name(hevy_title) == normalized:
            garmin = entry["garmin"]
            return ExerciseMatch(garmin["categoryId"], garmin["exerciseId"], 1.0)

    # Step 2: fuzzy match against lookup table hevy titles
    best_lookup_match: Optional[ExerciseMatch] = None
    best_lookup_score = 0.0
    for entry in lookup_table:
        hevy_title = entry.get("hevy", {}).get("exerciseTitle")
        if not hevy_title:
            continue
        score = calculate_similarity(normalized, hevy_title)
        if score > best_lookup_score and score > 0.7:
            best_lookup_score = score
            garmin = entry["garmin"]
            best_lookup_match = ExerciseMatch(garmin["categoryId"], garmin["exerciseId"], score)

    if best_lookup_match and best_lookup_score > 0.7:
        return best_lookup_match

    # Step 3: keyword-based fuzzy matching
    best_match: Optional[ExerciseMatch] = None
    best_score = 0.0
    for mapping in _KEYWORD_MAPPINGS:
        for keyword in mapping["keywords"]:
            score = calculate_similarity(normalized, keyword)
            if score > best_score and score > 0.5:
                best_score = score
                best_match = ExerciseMatch(mapping["category"], mapping["category_subtype"], score)

    if best_match and best_score > 0.6:
        return best_match

    # Step 4: fuzzy match against Garmin exercise names in the lookup table
    for entry in lookup_table:
        garmin = entry["garmin"]
        score = calculate_similarity(normalized, garmin["exerciseName"])
        if score > best_score and score > 0.5:
            best_score = score
            best_match = ExerciseMatch(garmin["categoryId"], garmin["exerciseId"], score)

    if not best_match or best_score < 0.5:
        return _TOTAL_BODY_FALLBACK

    return best_match
