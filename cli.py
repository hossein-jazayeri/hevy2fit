from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from config import load_config, convert_weight_to_kg
from csv_parser import parse_hevy_csv
from exercise_matcher import DEFAULT_LOOKUP_TABLE_PATH, load_lookup_table
from fit_writer import convert_activity_to_fit
from models import HevyActivity
from naming import filename_for_activity
from state import find_record, record_conversion, state_path_for
from workout_processor import group_rows_by_activity, order_activities, select_activity


def _load_activities(csv_path: Path) -> List[HevyActivity]:
    if not csv_path.exists():
        raise SystemExit(f"error: no such file: {csv_path}")
    if not csv_path.is_file():
        raise SystemExit(f"error: not a file: {csv_path}")

    content = csv_path.read_text(encoding="utf-8-sig")
    rows = parse_hevy_csv(content)
    if not rows:
        raise SystemExit(f"error: {csv_path} is empty or contains no valid rows")

    activities = group_rows_by_activity(rows)
    if not activities:
        raise SystemExit(f"error: no activities found in {csv_path}")

    return activities


def cmd_list(args: argparse.Namespace) -> None:
    csv_path = Path(args.csv)
    activities = _load_activities(csv_path)
    ordered = order_activities(activities)
    state_path = state_path_for(csv_path)

    for index, activity in enumerate(ordered):
        display_index = index - len(ordered)
        record = find_record(state_path, activity)
        status = f"  [converted {record['converted_at']}]" if record else ""
        print(
            f"[{display_index}] {activity.title!r}  "
            f"{activity.start_time} -> {activity.end_time}  "
            f"({len(activity.exercises)} exercises){status}"
        )


def cmd_convert(args: argparse.Namespace) -> None:
    csv_path = Path(args.csv)
    activities = _load_activities(csv_path)
    state_path = state_path_for(csv_path)

    config = load_config(Path(args.config) if args.config else None)
    weight = args.weight if args.weight is not None else config.weight
    unit = args.unit if args.unit is not None else config.unit
    met_value = args.met if args.met is not None else config.met_value
    rest_time = args.rest_time if args.rest_time is not None else config.rest_time
    exercise_time = args.exercise_time if args.exercise_time is not None else config.exercise_time

    if weight <= 0:
        raise SystemExit("error: --weight must be a positive number")

    weight_kg = convert_weight_to_kg(weight, unit)
    lookup_table_path = Path(args.lookup_table) if args.lookup_table else DEFAULT_LOOKUP_TABLE_PATH
    lookup_table = load_lookup_table(lookup_table_path)
    output_dir = Path(args.output_dir) if args.output_dir else csv_path.parent

    def convert_one(activity: HevyActivity, output_path: Path) -> None:
        fit_bytes = convert_activity_to_fit(
            activity,
            lookup_table,
            include_sets=not args.no_sets,
            weight_kg=weight_kg,
            met_value=met_value,
            rest_time_seconds=rest_time,
            exercise_time_seconds=exercise_time,
        )
        output_path.write_bytes(fit_bytes)
        record_conversion(state_path, activity, output_path)
        print(
            f"Wrote {output_path} ({len(fit_bytes)} bytes) from "
            f"{activity.title!r} [{activity.start_time} -> {activity.end_time}]"
        )

    if args.activity_index is not None:
        if args.output_dir:
            raise SystemExit("error: --output-dir only applies when converting all unconverted activities (omit --activity-index)")

        activity = select_activity(activities, args.activity_index)
        if activity is None:
            raise SystemExit("error: no matching activity (see `hevy2fit list` for valid --activity-index values)")

        existing_record = find_record(state_path, activity)
        if existing_record and not args.force:
            raise SystemExit(
                f"error: {activity.title!r} [{activity.start_time} -> {activity.end_time}] was already "
                f"converted at {existing_record['converted_at']} (output: {existing_record['output']}). "
                "Pass --force to convert it again."
            )

        output_path = Path(args.output) if args.output else output_dir / filename_for_activity(activity)
        convert_one(activity, output_path)
        return

    if args.output:
        raise SystemExit(
            "error: --output only applies to a single activity; pass --activity-index, or use "
            "--output-dir to set a directory for converting all unconverted activities"
        )

    converted_count = 0
    skipped_count = 0
    for activity in order_activities(activities):
        if find_record(state_path, activity) and not args.force:
            skipped_count += 1
            continue
        convert_one(activity, output_dir / filename_for_activity(activity))
        converted_count += 1

    if converted_count == 0:
        print(f"No new activities to convert ({skipped_count} already converted). Use --force to reconvert.")
    else:
        summary = f"Converted {converted_count} activit{'y' if converted_count == 1 else 'ies'}"
        if skipped_count:
            summary += f", skipped {skipped_count} already converted"
        print(summary + ".")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hevy2fit",
        description="Convert Hevy CSV workout exports to Garmin FIT files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List the activities found in a Hevy CSV export")
    list_parser.add_argument("csv", help="Path to the Hevy CSV export")
    list_parser.set_defaults(func=cmd_list)

    convert_parser = sub.add_parser(
        "convert", help="Convert Hevy CSV activities to Garmin FIT files"
    )
    convert_parser.add_argument("csv", help="Path to the Hevy CSV export")
    convert_parser.add_argument(
        "-o", "--output", help="Output .fit path for a single activity (requires --activity-index)"
    )
    convert_parser.add_argument(
        "--output-dir",
        help="Directory to write .fit files into when converting all unconverted activities "
        "(default: same directory as the CSV)",
    )
    convert_parser.add_argument(
        "--activity-index",
        type=int,
        default=None,
        help="Convert only this one activity, ordered oldest (0) to most recent (-1), instead of "
        "every unconverted activity. Run `hevy2fit list` to see indexes.",
    )
    convert_parser.add_argument(
        "--no-sets",
        action="store_true",
        help="Exclude per-set detail (reps/weight/duration), writing only the session/lap summary",
    )
    convert_parser.add_argument(
        "--force",
        action="store_true",
        help="Convert activities even if already converted before, per the state file next to the CSV",
    )
    convert_parser.add_argument(
        "--config", help="Path to a JSON config file with weight/unit/metValue/restTime/exerciseTime"
    )
    convert_parser.add_argument("--weight", type=float, help="Body weight, used for calorie estimation")
    convert_parser.add_argument("--unit", choices=["kg", "lbs"], help="Unit of --weight")
    convert_parser.add_argument("--met", type=float, help="MET value, used for calorie estimation (default: 5.0)")
    convert_parser.add_argument("--rest-time", type=int, help="Rest time in seconds between sets (default: 60)")
    convert_parser.add_argument(
        "--exercise-time", type=int, help="Duration in seconds attributed to each active set (default: 60)"
    )
    convert_parser.add_argument(
        "--lookup-table", help="Path to a custom exercise lookup table JSON (default: bundled table)"
    )
    convert_parser.set_defaults(func=cmd_convert)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
