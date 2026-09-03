from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.set_message import SetMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import (
    Event,
    EventType,
    FileType,
    FitBaseUnit,
    Manufacturer,
    SetType,
    Sport,
    SubSport,
)

from exercise_matcher import ExerciseMatch, find_exercise_match
from models import HevyActivity
from timestamps import parse_hevy_timestamp

_ACTIVE_SET_TYPES = ("normal", "warmup")


def _to_unix_ms(dt: datetime) -> int:
    return round(dt.timestamp() * 1000)


def estimate_calories_met(duration_seconds: float, weight_kg: float, met_value: float) -> int:
    """MET formula: calories = MET x weight(kg) x duration(hours)."""
    duration_hours = duration_seconds / 3600
    return round(met_value * weight_kg * duration_hours)


def convert_activity_to_fit(
    activity: HevyActivity,
    lookup_table: List[Dict[str, Any]],
    include_sets: bool = True,
    weight_kg: float = 70.0,
    met_value: float = 5.0,
    rest_time_seconds: int = 60,
    exercise_time_seconds: int = 60,
) -> bytes:
    builder = FitFileBuilder(auto_define=True)

    start_time = parse_hevy_timestamp(activity.start_time)
    end_time = parse_hevy_timestamp(activity.end_time)
    duration_seconds = round((end_time - start_time).total_seconds())
    total_calories = estimate_calories_met(duration_seconds, weight_kg, met_value)

    start_ms = _to_unix_ms(start_time)
    end_ms = _to_unix_ms(end_time)

    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.GARMIN.value
    file_id.product = 0
    file_id.time_created = start_ms
    file_id.serial_number = 0
    builder.add(file_id)

    device_info = DeviceInfoMessage()
    device_info.timestamp = start_ms
    device_info.device_index = 0
    device_info.manufacturer = Manufacturer.GARMIN.value
    device_info.product = 0
    device_info.product_name = "Hevy Converter"
    device_info.serial_number = 0
    device_info.software_version = 1.0
    builder.add(device_info)

    timer_start = EventMessage()
    timer_start.timestamp = start_ms
    timer_start.event = Event.TIMER
    timer_start.event_type = EventType.START
    builder.add(timer_start)

    session = SessionMessage()
    session.message_index = 0
    session.timestamp = end_ms
    session.start_time = start_ms
    session.sport = Sport.TRAINING
    session.sub_sport = SubSport.STRENGTH_TRAINING
    session.total_elapsed_time = duration_seconds
    session.total_timer_time = duration_seconds
    session.total_distance = 0
    session.total_calories = total_calories
    session.avg_speed = 0
    session.max_speed = 0
    session.avg_heart_rate = 0
    session.max_heart_rate = 0
    session.avg_cadence = 0
    session.max_cadence = 0
    session.total_ascent = 0
    session.total_descent = 0
    session.num_laps = 1
    session.first_lap_index = 0
    session.event_group = 0
    builder.add(session)

    lap = LapMessage()
    lap.message_index = 0
    lap.timestamp = end_ms
    lap.start_time = start_ms
    lap.total_elapsed_time = duration_seconds
    lap.total_timer_time = duration_seconds
    lap.total_distance = 0
    lap.total_calories = total_calories
    lap.avg_speed = 0
    lap.max_speed = 0
    lap.avg_heart_rate = 0
    lap.max_heart_rate = 0
    lap.avg_cadence = 0
    lap.max_cadence = 0
    lap.total_ascent = 0
    lap.total_descent = 0
    lap.event_group = 0
    builder.add(lap)

    activity_mesg = ActivityMessage()
    activity_mesg.timestamp = end_ms
    activity_mesg.total_timer_time = duration_seconds
    activity_mesg.num_sessions = 1
    activity_mesg.local_timestamp = 0
    builder.add(activity_mesg)

    timer_stop = EventMessage()
    timer_stop.timestamp = end_ms
    timer_stop.event = Event.TIMER
    timer_stop.event_type = EventType.STOP_ALL
    builder.add(timer_stop)

    if include_sets:
        _write_sets(
            builder=builder,
            activity=activity,
            lookup_table=lookup_table,
            start_time=start_time,
            rest_time_seconds=rest_time_seconds,
            exercise_time_seconds=exercise_time_seconds,
        )

    return builder.build_bytes()


def _write_sets(
    builder: FitFileBuilder,
    activity: HevyActivity,
    lookup_table: List[Dict[str, Any]],
    start_time: datetime,
    rest_time_seconds: int,
    exercise_time_seconds: int,
) -> None:
    # One workout step per unique exercise; sets reference it by index so Garmin
    # Connect can show the exercise name even though Set messages have no name field.
    exercise_to_step_index: Dict[str, int] = {}
    for exercise in activity.exercises:
        if exercise.exercise_title in exercise_to_step_index:
            continue
        step = WorkoutStepMessage()
        step.message_index = len(exercise_to_step_index)
        step.workout_step_name = exercise.exercise_title
        builder.add(step)
        exercise_to_step_index[exercise.exercise_title] = step.message_index

    exercise_time_delta = timedelta(seconds=exercise_time_seconds)
    rest_time_delta = timedelta(seconds=rest_time_seconds)
    match_cache: Dict[str, ExerciseMatch] = {}

    all_sets = []
    current_time = start_time
    for exercise in activity.exercises:
        step_index = exercise_to_step_index[exercise.exercise_title]
        for set_ in exercise.sets:
            if set_.weight_kg is None and set_.reps is None:
                continue

            if all_sets:
                current_time += rest_time_delta

            all_sets.append((set_, exercise.exercise_title, step_index, current_time))
            current_time += exercise_time_delta

    for message_index, (set_, exercise_title, step_index, timestamp) in enumerate(all_sets):
        if exercise_title not in match_cache:
            match_cache[exercise_title] = find_exercise_match(exercise_title, lookup_table)
        exercise_match = match_cache[exercise_title]

        timestamp_ms = _to_unix_ms(timestamp)
        weight_fit = float(round(set_.weight_kg)) if set_.weight_kg else 0.0

        set_message = SetMessage()
        set_message.timestamp = timestamp_ms
        set_message.start_time = timestamp_ms
        set_message.duration = exercise_time_seconds
        set_message.repetitions = int(set_.reps) if set_.reps else 0
        set_message.weight = weight_fit
        set_message.weight_display_unit = FitBaseUnit.KILOGRAM
        set_message.set_type = SetType.ACTIVE if set_.set_type in _ACTIVE_SET_TYPES else SetType.REST
        set_message.workout_step_index = step_index
        set_message.category = [exercise_match.category]
        set_message.category_subtype = [exercise_match.category_subtype]
        set_message.message_index = message_index
        builder.add(set_message)
