# hevy2fit

A command-line tool that converts a Hevy CSV workout export to a Garmin FIT file.

## Install

Run these commands from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The `pip install -e .` command installs the `hevy2fit` command and its one dependency, `fit-tool`.

Try it right away with the bundled sample export, before using your own data:

```bash
hevy2fit convert data/sample-workouts.csv
```

## Export your Hevy workouts

1. Open the Hevy web app and log in: https://hevy.com/
2. Go to https://hevy.com/settings?export
3. Export your workouts as a CSV file.

## List activities in a CSV file

The `list` command shows every activity in a CSV file, oldest first.

```bash
hevy2fit list workouts.csv
```

Each line shows an index, a title, a start and end time, and an exercise count:

```
[-2] 'Daily Pull'  3 Dec 2025, 10:40 -> 3 Dec 2025, 10:56  (3 exercises)
[-1] 'Weekend Long'  5 Dec 2025, 11:37 -> 5 Dec 2025, 12:55  (9 exercises)
```

Index `-1` is the most recent activity. Index `0` is the oldest. Use these indexes with `--activity-index` on the `convert` command.

## Convert a CSV file to FIT files

```bash
hevy2fit convert workouts.csv
```

By default, this command converts every activity that has not been converted before (see [Avoid duplicate activities](#avoid-duplicate-activities)) and writes one `.fit` file per activity into the same directory as the CSV. Each file is named after the activity's start time and title, for example `20260831-0655_Upper_A.fit`.

Run it again later, after a new Hevy export with more workouts, and it converts only the new ones:

```bash
hevy2fit convert workouts.csv
```
```
No new activities to convert (5 already converted). Use --force to reconvert.
```

Pass `--output-dir` to write the files somewhere other than the CSV's directory.

```bash
hevy2fit convert workouts.csv --output-dir ./fit-files
```

### Convert a single activity

Pass `--activity-index` to convert only one activity instead of every unconverted one. Run `hevy2fit list` first to see the available indexes; `-1` is the most recent activity, `0` is the oldest.

```bash
hevy2fit convert workouts.csv --activity-index -1
```

With `--activity-index`, use `-o` to choose the exact output path instead of the automatic name.

```bash
hevy2fit convert workouts.csv --activity-index -1 -o my-workout.fit
```

### Set body weight, MET value, and timing

The tool estimates calories from your body weight, a MET (Metabolic Equivalent of Task) value, and the workout duration. Pass these values as flags, or store them in a config file (see below).

```bash
hevy2fit convert workouts.csv --weight 84 --unit kg --met 6.0 --rest-time 30 --exercise-time 60
```

| Flag | Meaning | Default |
|---|---|---|
| `--weight` | Body weight, used for calorie estimation | 70 |
| `--unit` | Unit of `--weight`: `kg` or `lbs` | `kg` |
| `--met` | MET value, used for calorie estimation | 5.0 |
| `--rest-time` | Rest time in seconds between sets | 60 |
| `--exercise-time` | Duration in seconds attributed to each active set | 60 |

Hevy does not export the time spent on each exercise or rest period, so the tool applies a fixed duration to each set with `--exercise-time` and `--rest-time`. Adjust these values in Garmin Connect after import if needed.

### Use a config file instead of flags

Pass `--config` to load these values from a JSON file instead of typing them each time. A flag on the command line overrides the matching value in the config file.

```bash
hevy2fit convert workouts.csv --config config.json
```

`config.json`:

```json
{
  "weight": 84,
  "unit": "kg",
  "metValue": 6.0,
  "restTime": 30,
  "exerciseTime": 60
}
```

### Avoid duplicate activities

A Hevy export always contains your full workout history, not just new workouts. To stop you from converting (and re-uploading to Garmin Connect) the same activity twice, `convert` records each converted activity in a state file next to the CSV, named `<csv name>.hevy2fit-state.json`, and skips any activity already in it.

`list` marks already-converted activities the same way:

```
[-1] 'Weekend Long'  5 Dec 2025, 11:37 -> 5 Dec 2025, 12:55  (9 exercises)  [converted 2026-08-31T15:16:24+00:00]
```

If you convert a single activity with `--activity-index` and it was already converted, the command refuses and shows when:

```
error: 'Weekend Long' [5 Dec 2025, 11:37 -> 5 Dec 2025, 12:55] was already converted at 2026-08-31T15:16:24+00:00 (output: workouts.fit). Pass --force to convert it again.
```

Pass `--force` to convert activities again anyway, for example after you change `--weight` or `--met` and want to regenerate the files.

```bash
hevy2fit convert workouts.csv --force
```

### Exclude set detail

Pass `--no-sets` to write only the session and lap summary, without per-set data (reps, weight, duration).

```bash
hevy2fit convert workouts.csv --no-sets
```

### Exercise name matching

Garmin does not accept free-text exercise names, so the tool maps each Hevy exercise name to a Garmin exercise category and ID. It checks the lookup table at `data/exercise-lookup-table.json` first, then falls back to fuzzy matching. If an exercise gets mapped to the wrong Garmin exercise, add or edit an entry in that file, or point to a different table with `--lookup-table`.

```bash
hevy2fit convert workouts.csv --lookup-table my-lookup-table.json
```

## Upload the FIT file to Garmin Connect

1. Go to https://connect.garmin.com and log in.
2. Click **Activities**, then **Import Data**.
3. Choose the `.fit` file you created and upload it.
4. Open the imported activity under **Activities** > **All Activities** and check the start time, end time, duration, and exercise details.

## Command reference

```bash
hevy2fit --help
hevy2fit list --help
hevy2fit convert --help
```
