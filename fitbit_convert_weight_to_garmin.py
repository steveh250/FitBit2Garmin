#!/usr/bin/env python3
"""
Convert a Fitbit weight export CSV into the Garmin Connect weight-import format.

Input (Fitbit export) columns:
    timestamp, weight grams, data source

Output (Garmin import) format:
    Body                                <- literal title line required by Garmin's importer
    Date,Weight,BMI,Fat                 <- Garmin's expected header
    6/15/2026,63.32,0,0                 <- one row per weigh-in

Reformatting decisions, and why:

1. "Body" title line
   Garmin's weight-import tool expects the file to start with a literal
   "Body" line before the actual CSV header. Without it, the importer
   doesn't recognize the file as a weight/body-composition import.

2. Date column (was "timestamp")
   - Fitbit gives a full ISO-8601 UTC timestamp, e.g. 2020-07-20T06:59:59Z.
   - Garmin's format only wants a date, no time, in M/D/YYYY form
     (no zero-padding on month/day, 4-digit year) e.g. 7/20/2020.
   - We parse the ISO timestamp and re-emit just the date portion.
   - NOTE: We deliberately do NOT do any timezone conversion here -- we
     keep the calendar date exactly as Fitbit recorded it (the date
     portion of the UTC timestamp). If your weigh-ins were close to
     midnight UTC, this *could* shift the date by one day relative to
     your local time. Spot-check a few entries if exact dates matter.

3. Weight column (was "weight grams")
   - Fitbit stores weight in grams as an integer (e.g. 59421).
   - Garmin's format wants kilograms as a decimal (e.g. 59.42).
   - We divide by 1000 and round to 2 decimal places.

4. BMI and Fat columns (new, did not exist in Fitbit export)
   - Fitbit's export doesn't include BMI or body fat % in this file.
   - Garmin's importer requires these columns to be present, so per your
     note we hardcode both to 0 for every row to allow the import to
     succeed. If you have real BMI/Fat data elsewhere, you could populate
     these instead of zeroing them.

5. "data source" column (dropped entirely)
   - Garmin's format has no equivalent field, so this column is simply
     discarded during conversion. No information from it carries over.

6. Row order / outliers
   - This script does not filter, sort, or de-duplicate rows -- it's a
     straight pass-through transformation. If your source has bad data
     (e.g. an outlier weight reading), clean that up in the input CSV
     before running this script, since the script will faithfully
     convert whatever it's given.
"""

import csv
import sys
from datetime import datetime


def convert(infile, outfile):
    with open(infile, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows_out = []

        for row in reader:
            # --- Date: strip time, reformat to M/D/YYYY ---
            # Some Fitbit timestamps include fractional seconds
            # (e.g. 2026-05-25T14:39:06.744Z) while others don't
            # (e.g. 2020-07-20T06:59:59Z). datetime.fromisoformat()
            # handles both, once we swap the trailing "Z" for "+00:00"
            # (fromisoformat doesn't accept "Z" as a UTC marker).
            ts = row["timestamp"].strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            date_str = f"{dt.month}/{dt.day}/{dt.year}"

            # --- Weight: grams -> kg, 2 decimal places ---
            grams = float(row["weight grams"])
            weight_kg = round(grams / 1000, 2)

            # --- BMI / Fat: not present in source, required by Garmin ---
            rows_out.append({
                "Date": date_str,
                "Weight": weight_kg,
                "BMI": 0,
                "Fat": 0,
            })

    with open(outfile, "w", newline="", encoding="utf-8") as f_out:
        # Literal "Body" title line required by Garmin's importer
        f_out.write("Body\n")

        writer = csv.DictWriter(f_out, fieldnames=["Date", "Weight", "BMI", "Fat"])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Converted {len(rows_out)} rows -> {outfile}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_weight.py input.csv output.csv")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])

