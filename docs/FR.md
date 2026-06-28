# Functional Requirements

> **Gherkin note.** The build standard expects functional requirements to be
> derived from Gherkin `.feature` files. **No `.feature` files exist in this
> repository**, and no base Gherkin set was supplied with the code. The
> requirements below are therefore reverse-engineered from the scripts' actual
> behaviour and expressed in Given/When/Then form so they can later be promoted
> to Gherkin scenarios. The "Gherkin reference" column names the *proposed*
> Feature / Scenario each requirement would map to.

## Status legend

`Implemented` — present and verified · `Partial` — present with caveats ·
`Not Started` — not yet built.

## Activities converter (`fitbit_activities_to_garmin.py`)

| ID | Requirement | Gherkin reference (proposed) | Status |
| --- | --- | --- | --- |
| FR-1 | Discover metric folders by fuzzy, case/punctuation-insensitive name matching, searching recursively. | Activities Discovery / "Match metric folders regardless of naming style" | Implemented |
| FR-2 | Parse both JSON and CSV files within a single metric folder. | Activities Parsing / "Read mixed JSON and CSV files" | Implemented |
| FR-3 | Auto-detect CSV delimiter (tab vs. comma) per file and match columns case-insensitively. | Activities Parsing / "Auto-detect delimiter and columns" | Implemented |
| FR-4 | Treat all timestamps as UTC and convert to a configurable local timezone before assigning a calendar day. | Activities Timezone / "Bucket readings by local day" | Implemented |
| FR-5 | Sum each metric's readings into one value per day. | Activities Aggregation / "Total readings per day" | Implemented |
| FR-6 | Merge all metrics over the union of dates into one date-keyed table. | Activities Aggregation / "Combine metrics into one row per day" | Implemented |
| FR-7 | Convert distance from meters to kilometres (÷1000, 2 dp). | Activities Conversion / "Convert distance to km" | Partial (unit assumed, unverified) |
| FR-8 | Default missing metrics to 0 (with warning); fall back `Activity Calories` → `Calories Burned`. | Activities Defaults / "Handle absent metrics" | Implemented |
| FR-9 | Write Garmin Activities CSV split by calendar year, with the literal `Activities` title line and quoted values. | Activities Output / "Emit per-year Garmin CSV" | Implemented |
| FR-10 | Skip malformed files and rows with a warning instead of aborting the run. | Activities Resilience / "Tolerate bad records" | Implemented |
| FR-11 | Accept `export_folder`, `output_dir`, and `--timezone`; validate the timezone and that the export path is a directory, exiting `1` on error. | Activities CLI / "Validate arguments" | Implemented |

## Weight converter (`fitbit_convert_weight_to_garmin.py`)

| ID | Requirement | Gherkin reference (proposed) | Status |
| --- | --- | --- | --- |
| FR-12 | Read a Fitbit weight CSV with `timestamp`, `weight grams`, `data source` columns. | Weight Parsing / "Read Fitbit weight export" | Implemented |
| FR-13 | Reformat the ISO-8601 UTC timestamp to `M/D/YYYY` (date only, no timezone conversion), handling optional fractional seconds. | Weight Date / "Emit calendar date" | Implemented |
| FR-14 | Convert weight from grams to kilograms, rounded to 2 dp. | Weight Conversion / "Convert grams to kg" | Implemented |
| FR-15 | Add `BMI` and `Fat` columns fixed at 0; drop the `data source` column. | Weight Columns / "Shape Garmin body columns" | Implemented |
| FR-16 | Write a Garmin `Body` CSV with the literal title line and header row. | Weight Output / "Emit Garmin Body CSV" | Implemented |
| FR-17 | Require exactly two CLI arguments (input, output); print usage and exit `1` otherwise. | Weight CLI / "Validate arguments" | Implemented |

## Acceptance criteria (Given / When / Then)

- **FR-1** — *Given* an export with a folder named `Floors-Climbed` (or
  `Floors Climbed`), *when* the script scans it, *then* the folder is matched to
  the `floors` metric.
- **FR-2 / FR-3** — *Given* a metric folder containing a `.json` file and a
  tab-separated `.csv` file with a `distance` column, *when* aggregated, *then*
  values from both files are summed correctly.
- **FR-4** — *Given* a JSON reading at `06/25/26 23:30:00` (UTC) with
  `--timezone America/Vancouver`, *when* bucketed, *then* it is counted under
  `2026-06-25` (16:30 local), not the next day.
- **FR-6 / FR-8** — *Given* a day with steps but no `Minutes Sedentary` folder,
  *when* the table is built, *then* a row still exists for that day with
  `Minutes Sedentary = 0`.
- **FR-9** — *Given* aggregated 2026 data, *when* writing output, *then*
  `Activities_2026.csv` begins with an `Activities` line followed by the header.
- **FR-10** — *Given* a CSV row with a non-numeric value, *when* aggregating,
  *then* that row is skipped and processing continues.
- **FR-11 / FR-17** — *Given* an invalid timezone or a missing argument, *when*
  the script runs, *then* it prints an explanatory error and exits with code 1.
- **FR-13 / FR-14** — *Given* `2020-07-20T06:59:59Z, 59421`, *when* converted,
  *then* the output row is `7/20/2020,59.42,0,0`.

## Omitted base scenarios

No base Gherkin scenario set was provided with this build, so none are
enumerated as omitted here. Capabilities deliberately **out of scope** (and thus
not represented as FRs): live Fitbit/Garmin API access, automated upload,
authentication, a GUI/web interface, and non-activity/weight metrics
(sleep, heart rate, SpO₂).
