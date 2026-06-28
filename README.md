# FitBit2Garmin

Two small, dependency-free Python scripts for converting a local **Fitbit data
export** into the CSV formats that **Garmin Connect's import tools** expect.

Both scripts work entirely offline — they read files already on disk and write
new files. There are no Fitbit or Garmin API calls, no authentication, and no
network access of any kind.

| Script | Converts | Produces |
| --- | --- | --- |
| [`fitbit_activities_to_garmin.py`](#fitbit_activities_to_garminpy) | A folder of daily-activity metrics (steps, calories, distance, floors, active minutes) | One `Activities_<year>.csv` per calendar year |
| [`fitbit_convert_weight_to_garmin.py`](#fitbit_convert_weight_to_garminpy) | A single Fitbit weight-export CSV | One Garmin `Body` weight-import CSV |

## Requirements

- **Python 3.9+** (uses the standard-library `zoneinfo` module).
- No third-party packages — only the Python standard library.

On some minimal Linux installs you may need the system tz database for
`zoneinfo` to resolve IANA timezone names (e.g. `apt install tzdata`).

---

## `fitbit_activities_to_garmin.py`

Scans a Fitbit export folder made up of top-level metric folders (e.g.
`Calories`, `Distance`, `Floors Climbed`, `Steps`), reduces every file inside
each folder to one number per day, merges all metrics into a single
date-keyed table, and writes it out in Garmin's Activities CSV format, split
by year.

### Usage

```bash
python fitbit_activities_to_garmin.py /path/to/export_folder /path/to/output_dir [--timezone TZ_NAME]
```

| Argument | Required | Description |
| --- | --- | --- |
| `export_folder` | yes | Path to the Fitbit export folder to scan |
| `output_dir` | yes | Where to write `Activities_<year>.csv` files (created if missing) |
| `--timezone` | no | IANA timezone name for day-bucketing (default: `America/Vancouver`) |

Example:

```bash
python fitbit_activities_to_garmin.py ~/Downloads/MyFitbitData ./out --timezone Europe/London
```

### How it works

- **Folder matching** is case-insensitive and fuzzy: punctuation and spaces are
  stripped, so `Floors Climbed`, `floors`, and `Floors_Climbed` all map to the
  same metric. The export may also be nested a level or two deep — the scan
  walks recursively. If a metric folder isn't found, that column defaults to `0`
  for every day and a warning is printed.
- **File parsing** (per file inside a metric folder):
  - `.json` — Fitbit's standard `[{"dateTime": "...", "value": "..."}]` shape,
    with `dateTime` in `MM/DD/YY HH:MM:SS`.
  - `.csv` — delimiter (tab vs comma) is auto-detected, then a timestamp-like
    column (`timestamp`/`datetime`/`date`) and a value-like column (the
    metric's name, or `value`) are matched case-insensitively. CSV timestamps
    are assumed ISO 8601 (e.g. `2019-06-09T16:46:00Z`).
  - Any other file type is ignored.
  - Malformed individual rows are skipped rather than failing the whole file.

### Timezone handling

All Fitbit timestamps in this export — both the JSON `dateTime` strings (which
*look* local but have no timezone marker) and the CSV `...Z` timestamps — are
treated as **UTC** and converted to the chosen local timezone before deciding
which calendar day a reading belongs to. This was verified against the Fitbit
app: treating the JSON timestamps as UTC and converting to local time matched
the app's daily totals exactly, while treating them as already-local did not.

### Output format

One file per year, e.g. `Activities_2021.csv`:

```
Activities
Date,Calories Burned,Steps,Distance,Floors,Minutes Sedentary,Minutes Lightly Active,Minutes Fairly Active,Minutes Very Active,Activity Calories
"2021-08-01","5383","45726","36.04","0","583","225","33","337","4170"
```

The leading `Activities` title line is required by Garmin's importer to
recognize the file type.

### Assumptions worth verifying

- **Distance** values are assumed to be in **meters** per record, summed per
  day and divided by 1000 for km (see `DISTANCE_UNIT_TO_KM` near the top of the
  script). Spot-check a known day against your Fitbit dashboard; if it's far
  off, adjust that constant.
- **Activity Calories** has no dedicated folder in this export, so it falls back
  to mirroring **Calories Burned** for each day.

---

## `fitbit_convert_weight_to_garmin.py`

Converts a single Fitbit weight-export CSV into Garmin Connect's
weight/body-composition import format.

### Usage

```bash
python fitbit_convert_weight_to_garmin.py input.csv output.csv
```

### Conversion details

Input (Fitbit) columns: `timestamp`, `weight grams`, `data source`.

| Garmin column | Source | Transformation |
| --- | --- | --- |
| `Date` | `timestamp` | ISO-8601 UTC timestamp → `M/D/YYYY` (date portion only, **no** timezone conversion) |
| `Weight` | `weight grams` | grams → kilograms, rounded to 2 decimals |
| `BMI` | — | hardcoded to `0` (not in Fitbit export, required by Garmin) |
| `Fat` | — | hardcoded to `0` (not in Fitbit export, required by Garmin) |
| — | `data source` | dropped |

The output starts with a literal `Body` title line required by Garmin's
importer:

```
Body
Date,Weight,BMI,Fat
7/20/2020,59.42,0,0
```

### Notes

- The date keeps the calendar day exactly as Fitbit recorded it (the UTC date),
  with **no** timezone conversion. Weigh-ins near midnight UTC could land on a
  different local day — spot-check if exact dates matter.
- This is a straight pass-through: rows are not filtered, sorted, or
  de-duplicated. Clean up outliers in the input CSV before running.

---

## General workflow

1. Export your data from Fitbit (Account → Data Export / "Export Your Account
   Archive").
2. Run the relevant script above against the exported files.
3. **Spot-check** a few output rows against your Fitbit dashboard for a known
   day before importing — especially Distance and any near-midnight dates.
4. Import the resulting CSV(s) into Garmin Connect.
