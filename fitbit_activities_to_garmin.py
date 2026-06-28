#!/usr/bin/env python3
"""
fitbit_activities_to_garmin.py

Scans a local Fitbit data-export folder structured as top-level metric
folders (e.g. "Calories", "Distance", "Floors Climbed", "Steps"), each
containing a mix of JSON and CSV files. No network access, no Fitbit/Garmin
API calls -- reads only files already on disk.

APPROACH (matches the logic you described):
  1. For each known metric folder, read every file inside it (JSON or CSV,
     whatever extension), and reduce it to one number per day.
  2. Merge all metrics into a single table keyed by date.
  3. Write that table out as Garmin's "Activities" CSV format, split by year.

Garmin's expected output format (confirmed from Garmin's own import docs):

    Activities
    Date,Calories Burned,Steps,Distance,Floors,Minutes Sedentary,Minutes Lightly Active,Minutes Fairly Active,Minutes Very Active,Activity Calories
    "2021-08-01","5383","45726","36.04","0","583","225","33","337","4170"

HOW FOLDER MATCHING WORKS:
Folder names are matched case-insensitively and somewhat fuzzily, so
"Floors Climbed", "floors", "Floors_Climbed" etc. all map to the "floors"
metric. If a metric folder isn't found at all, that column defaults to 0
for every day and a warning is printed.

HOW FILE PARSING WORKS (per file inside a metric folder):
  - .json  -> assumed Fitbit's standard [{"dateTime": "...", "value": "..."}]
              shape, with dateTime in "%m/%d/%y %H:%M:%S".
  - .csv   -> auto-detects tab vs comma delimiter, then looks for a
              timestamp-like column (timestamp/datetime/date) and a
              value-like column (the metric's own name, or "value"),
              matched case-insensitively. Timestamps assumed ISO 8601
              (e.g. "2019-06-09T16:46:00Z").

ASSUMPTIONS TO VERIFY AGAINST YOUR OWN DATA:
  - Distance values (your CSV sample: "8.8", "6.8") are assumed to be in
    METERS per record. Summed per day, divided by 1000 for km. Sanity-check
    a known day against your Fitbit dashboard -- if it's way off, adjust
    DISTANCE_UNIT_TO_KM below.
  - "Activity Calories" (last output column) defaults to equal "Calories
    Burned" since there's no separate folder for it in your export.

CONFIRMED (not an assumption): ALL Fitbit timestamps in this export --
both the JSON dateTime strings and the CSV "...Z" timestamps -- are UTC,
even though the JSON ones have no timezone marker and look local. This was
verified by summing June 25, 2026 steps directly from the raw JSON: treating
the timestamp as UTC and converting to Pacific time gave 3,569 steps,
matching the Fitbit app exactly; treating it as already-local gave 5,095,
which did not match. So every timestamp in this script is converted
UTC -> LOCAL_TZ before its calendar day is determined.

Usage:
    python fitbit_activities_to_garmin.py /path/to/export_folder /path/to/output_dir [--timezone TZ_NAME]

    --timezone defaults to "America/Vancouver". Pass any IANA timezone name
    (e.g. America/New_York, Europe/London, Asia/Tokyo) if you're converting
    data recorded in a different region.
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ---- Tunable assumptions (see header notes) --------------------------------
DISTANCE_UNIT_TO_KM = 1 / 1000  # assume meters; multiply by this to get km
JSON_DATETIME_FORMAT = "%m/%d/%y %H:%M:%S"

# Default local timezone, used unless overridden by the --timezone command
# line argument (see main()). Fitbit's timestamps -- both the JSON
# dateTime strings and the CSV "...Z" timestamps -- are UTC (confirmed by
# direct testing against the Fitbit app; the JSON ones have no timezone
# marker but are UTC anyway). Every timestamp gets converted into this
# timezone before determining which calendar day a reading belongs to.
DEFAULT_TIMEZONE = "America/Vancouver"

# Set by main() from the --timezone argument; parse_day_any_format() reads
# this at call time, so it must be set before any parsing happens.
LOCAL_TZ = ZoneInfo(DEFAULT_TIMEZONE)

# Maps internal metric name -> list of normalized folder-name fragments that
# should match it. Matching is done by lowercasing and stripping spaces/
# underscores, so "Floors Climbed" -> "floorsclimbed".
METRIC_FOLDER_ALIASES = {
    "steps": ["steps"],
    "calories": ["calories"],
    "distance": ["distance"],
    "floors": ["floorsclimbed", "floors"],
    "minutes_sedentary": ["minutessedentary"],
    "minutes_lightly_active": ["minuteslightlyactive"],
    # Fitbit uses "Moderately Active" in some exports, "Fairly Active" in
    # others -- both map to Garmin's "Minutes Fairly Active" column.
    "minutes_fairly_active": ["minutesfairlyactive", "minutesmoderatelyactive"],
    "minutes_very_active": ["minutesveryactive"],
    "activity_calories": ["activitycalories"],
}

# Candidate CSV column names per metric (checked case-insensitively, in
# addition to the generic "value" fallback).
METRIC_VALUE_COLUMN_HINTS = {
    "steps": ["steps"],
    "calories": ["calories"],
    "distance": ["distance"],
    "floors": ["floors"],
    "minutes_sedentary": ["minutessedentary"],
    "minutes_lightly_active": ["minuteslightlyactive"],
    "minutes_fairly_active": ["minutesfairlyactive", "minutesmoderatelyactive"],
    "minutes_very_active": ["minutesveryactive"],
    "activity_calories": ["activitycalories"],
}

TIME_COLUMN_HINTS = ["timestamp", "datetime", "date"]


def normalize(name: str) -> str:
    # Strip everything except letters/digits and lowercase it, so folder
    # names like "Floors Climbed", "floors_climbed", "Floors-Climbed" all
    # collapse to the same string ("floorsclimbed") for matching purposes.
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_metric_folders(export_folder: Path):
    """
    Walk top-level (and one level deep, in case of nesting) subfolders of
    export_folder and map each known metric to the folder(s) that match it.
    """
    # rglob("*") walks recursively, so this also tolerates the export being
    # nested a level or two deeper than expected (e.g. inside a "Fitbit"
    # subfolder) without needing a separate code path.
    candidate_folders = [p for p in export_folder.rglob("*") if p.is_dir()]
    metric_to_folders = defaultdict(list)

    for folder in candidate_folders:
        norm = normalize(folder.name)
        for metric_name, aliases in METRIC_FOLDER_ALIASES.items():
            # Substring match (not exact match) so "Minutes Moderately
            # Active" matches alias "minutesmoderatelyactive" even if the
            # real folder name has extra words around it.
            if any(alias in norm for alias in aliases):
                metric_to_folders[metric_name].append(folder)
                break  # don't let one folder match multiple metrics

    return metric_to_folders


def parse_day_any_format(raw: str) -> str:
    """
    Convert a Fitbit timestamp string to "YYYY-MM-DD" in LOCAL_TZ.

    CONFIRMED BY DIRECT TESTING (not just an assumption): Fitbit's JSON
    dateTime strings (e.g. "06/25/26 14:30:00") look naive/local but are
    actually UTC, same as the "...Z" CSV timestamps -- just without the Z
    marker. Verified by comparing a known day's step total against the
    Fitbit app: treating the JSON value as UTC and converting to Pacific
    time matched the app exactly; treating it as already-local did not.
    So both JSON and CSV timestamps get the same UTC -> LOCAL_TZ treatment.
    """
    raw = raw.strip()
    if raw.endswith("Z"):
        # CSV-style ISO timestamp, explicitly marked UTC.
        dt_utc = datetime.fromisoformat(raw[:-1]).replace(tzinfo=ZoneInfo("UTC"))
        dt_local = dt_utc.astimezone(LOCAL_TZ)
        return dt_local.strftime("%Y-%m-%d")
    try:
        # Some CSV exports use ISO format without a trailing Z.
        dt_naive = datetime.fromisoformat(raw)
    except ValueError:
        # Otherwise it's the JSON-style "MM/DD/YY HH:MM:SS" format.
        dt_naive = datetime.strptime(raw, JSON_DATETIME_FORMAT)
    # Regardless of which format it was, treat the naive value as UTC
    # (confirmed by testing -- see module docstring) and convert to local
    # time before reporting which calendar day it falls on.
    dt_utc = dt_naive.replace(tzinfo=ZoneInfo("UTC"))
    dt_local = dt_utc.astimezone(LOCAL_TZ)
    return dt_local.strftime("%Y-%m-%d")


def find_key(d: dict, candidates):
    """Case-insensitive lookup of the first matching key from candidates."""
    # Build a lowercase->original lookup once per call, then check each
    # candidate name in priority order (metric-specific name first, then
    # the generic "value" fallback -- see how value_hints is built above).
    lower_map = {k.lower(): k for k in d.keys()}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def read_json_records(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # A handful of Fitbit exports wrap a single reading in an object
        # instead of a one-item list -- normalize so callers always get a
        # list to iterate over.
        data = [data]
    return data


def read_csv_records(file_path: Path):
    with file_path.open("r", encoding="utf-8", newline="") as f:
        # Sniff the delimiter rather than assuming -- Distance came as
        # tab-separated, other metrics may be comma-separated, and this
        # avoids needing a per-metric delimiter setting.
        sample = f.read(4096)
        f.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        return list(reader)


def aggregate_metric_folder(folders, metric_name):
    """
    Read every file inside the given folder(s) for one metric (JSON or CSV,
    mixed) and sum values by day. Returns dict: {date_str: summed_value}
    """
    daily_totals = defaultdict(float)
    # Metric-specific column name (e.g. "distance") tried first, generic
    # "value" tried as a fallback -- covers both the JSON convention and
    # whatever a particular CSV happens to call its data column.
    value_hints = METRIC_VALUE_COLUMN_HINTS.get(metric_name, []) + ["value"]
    files_processed = 0

    for folder in folders:
        for file_path in sorted(folder.iterdir()):
            if not file_path.is_file():
                continue
            suffix = file_path.suffix.lower()
            try:
                if suffix == ".json":
                    records = read_json_records(file_path)
                    # JSON files consistently use these two key names
                    # across every Fitbit metric, so no need to guess.
                    time_key_candidates, value_key_candidates = ["dateTime"], ["value"]
                elif suffix == ".csv":
                    records = read_csv_records(file_path)
                    time_key_candidates, value_key_candidates = TIME_COLUMN_HINTS, value_hints
                else:
                    # Anything that isn't .json or .csv is ignored (e.g.
                    # stray readme/index files Fitbit sometimes includes).
                    continue
            except (json.JSONDecodeError, OSError, csv.Error) as e:
                print(f"  Warning: could not read {file_path.name}: {e}")
                continue

            if not records:
                continue

            # Only need to detect column names once per file, from the
            # first record -- assumes consistent columns within one file.
            time_key = find_key(records[0], time_key_candidates)
            value_key = find_key(records[0], value_key_candidates)
            if time_key is None or value_key is None:
                print(f"  Warning: {file_path.name} ({metric_name}) -- could not "
                      f"identify time/value columns (found: {list(records[0].keys())}). Skipping.")
                continue

            for record in records:
                try:
                    day = parse_day_any_format(str(record[time_key]))
                    value = float(record[value_key])
                except (KeyError, ValueError):
                    # Skip individual malformed rows rather than failing
                    # the whole file over one bad record.
                    continue
                daily_totals[day] += value

            files_processed += 1

    print(f"  {metric_name}: {files_processed} file(s) processed across {len(folders)} folder(s)")
    return daily_totals


def build_activities_table(export_folder: Path):
    print("Scanning for metric folders...")
    metric_to_folders = find_metric_folders(export_folder)

    for metric_name in METRIC_FOLDER_ALIASES:
        if metric_name not in metric_to_folders:
            print(f"  {metric_name}: NO MATCHING FOLDER FOUND (will default to 0)")
        else:
            names = ", ".join(f.name for f in metric_to_folders[metric_name])
            print(f"  {metric_name}: matched folder(s) -> {names}")

    print("\nAggregating daily totals per metric...")
    metric_daily = {}
    for metric_name in METRIC_FOLDER_ALIASES:
        folders = metric_to_folders.get(metric_name, [])
        if not folders:
            metric_daily[metric_name] = {}
            continue
        metric_daily[metric_name] = aggregate_metric_folder(folders, metric_name)

    all_dates = set()
    for daily in metric_daily.values():
        # Union of every date seen across all metrics, not just the
        # intersection -- so a day with steps but no recorded distance
        # still gets a row (with distance defaulting to 0 below).
        all_dates.update(daily.keys())

    if not all_dates:
        return {}

    table = {}
    for day in all_dates:
        steps = metric_daily["steps"].get(day, 0)
        calories = metric_daily["calories"].get(day, 0)
        distance_raw = metric_daily["distance"].get(day, 0)
        distance_km = distance_raw * DISTANCE_UNIT_TO_KM if distance_raw else 0
        floors = metric_daily["floors"].get(day, 0)
        min_sedentary = metric_daily["minutes_sedentary"].get(day, 0)
        min_lightly = metric_daily["minutes_lightly_active"].get(day, 0)
        min_fairly = metric_daily["minutes_fairly_active"].get(day, 0)
        min_very = metric_daily["minutes_very_active"].get(day, 0)
        # No dedicated Activity Calories folder in this export, so it
        # falls back to mirroring Calories Burned for that day.
        activity_calories = metric_daily["activity_calories"].get(day, calories)

        table[day] = {
            "Calories Burned": int(round(calories)),
            "Steps": int(round(steps)),
            "Distance": round(distance_km, 2),
            "Floors": int(round(floors)),
            "Minutes Sedentary": int(round(min_sedentary)),
            "Minutes Lightly Active": int(round(min_lightly)),
            "Minutes Fairly Active": int(round(min_fairly)),
            "Minutes Very Active": int(round(min_very)),
            "Activity Calories": int(round(activity_calories)),
        }

    return table


def write_activities_csv(table, output_dir: Path):
    if not table:
        print("No activity data found -- nothing to write.")
        return

    by_year = defaultdict(list)
    for day in sorted(table.keys()):
        # Garmin's importer wants one file per calendar year, so split
        # the combined table back apart by year before writing.
        by_year[day[:4]].append(day)

    output_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        "Calories Burned", "Steps", "Distance", "Floors",
        "Minutes Sedentary", "Minutes Lightly Active",
        "Minutes Fairly Active", "Minutes Very Active",
        "Activity Calories",
    ]

    for year, days in sorted(by_year.items()):
        out_path = output_dir / f"Activities_{year}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            # Garmin's format has a one-word section header line ("Activities")
            # before the real column header row -- not standard CSV, but
            # required for the importer to recognize the file type.
            f.write("Activities\n")
            f.write("Date," + ",".join(columns) + "\n")
            for day in days:
                row = table[day]
                values = ",".join(f'"{row[col]}"' for col in columns)
                f.write(f'"{day}",{values}\n')
        print(f"Wrote {len(days)} day(s) to {out_path}")


def main():
    global LOCAL_TZ

    parser = argparse.ArgumentParser(
        description="Convert a local Fitbit export folder into Garmin Connect's Activities CSV format."
    )
    parser.add_argument("export_folder", help="Path to the Fitbit export folder to scan")
    parser.add_argument("output_dir", help="Path to write Activities_<year>.csv files to")
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help=(
            "IANA timezone name to convert UTC timestamps into before "
            f"bucketing by calendar day (default: {DEFAULT_TIMEZONE}). "
            "Examples: America/Vancouver, America/New_York, Europe/London."
        ),
    )
    args = parser.parse_args()

    try:
        LOCAL_TZ = ZoneInfo(args.timezone)
    except Exception as e:
        print(f"Error: '{args.timezone}' is not a recognized timezone name: {e}")
        print("Use an IANA timezone identifier, e.g. America/Vancouver, Europe/London, Asia/Tokyo.")
        sys.exit(1)

    export_folder = Path(args.export_folder)
    output_dir = Path(args.output_dir)

    if not export_folder.is_dir():
        print(f"Error: {export_folder} is not a valid directory")
        sys.exit(1)

    print(f"Timezone for day-bucketing: {args.timezone}")
    print(f"Distance conversion: assuming raw unit is meters, x{DISTANCE_UNIT_TO_KM} -> km")
    print(f"JSON datetime format assumed: {JSON_DATETIME_FORMAT}")
    print("CSV timestamps assumed ISO 8601 (e.g. 2019-06-09T16:46:00Z)\n")

    table = build_activities_table(export_folder)
    write_activities_csv(table, output_dir)

    print("\nDone. Before importing into Garmin, spot-check a few rows against")
    print("your Fitbit dashboard for a known day -- especially Distance, since")
    print("the unit conversion is an assumption, not a confirmed spec.")
    print("\nIf any metric showed 'NO MATCHING FOLDER FOUND' above, check the")
    print("actual folder name in your export and tell me -- METRIC_FOLDER_ALIASES")
    print("may need a new alias added.")


if __name__ == "__main__":
    main()
