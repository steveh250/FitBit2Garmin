# Test Cases

> **Testing note.** There is **no automated test suite** in this repository yet
> (tracked as NFR-11). The cases below are **manual** and were executed by
> running the scripts against small synthetic fixtures. Results recorded here
> reflect actual observed output from those runs. Each case links to a
> requirement in `docs/FR.md` / `docs/NFR.md`.

## Summary

| Category | Total | Passing | Failing | Notes |
| --- | --- | --- | --- | --- |
| Unit | 0 | 0 | 0 | No unit-test harness yet (NFR-11). |
| Integration (manual) | 9 | 9 | 0 | Whole-script runs on synthetic fixtures. |
| End-to-end | — | — | — | Final import into Garmin Connect not automatable here. |
| Security | 1 | 1 | 0 | Confirmed no network/credential use. |
| Performance | 1 | 1 | 0 | Sub-second on the sample fixture. |
| **Total** | **11** | **11** | **0** | Requirement coverage: every FR/NFR marked `Implemented`/`Met` has ≥1 case (manual). Automated coverage: **0%**. |

## Integration tests (manual)

### TC-1 — Mixed JSON/CSV aggregation with fuzzy folders
- **Requirement:** FR-1, FR-2, FR-3, FR-5, FR-6
- **Preconditions:** Export with `Steps/steps1.json`, `Floors Climbed/floors.json`,
  `Distance/dist.csv` (tab-separated, `distance` column, `...Z` timestamps),
  `Calories/cal.json`.
- **Steps:** `python3 fitbit_activities_to_garmin.py export out --timezone America/Vancouver`
- **Expected:** All four folders matched; one row for `2026-06-25`; steps summed
  to 150; floors 3.
- **Result:** **PASS** — row `"2026-06-25","1001","150","0.02","3",...` produced.

### TC-2 — UTC→local day bucketing
- **Requirement:** FR-4
- **Preconditions:** A steps reading at `06/25/26 23:30:00` (UTC).
- **Steps:** Run with `--timezone America/Vancouver`.
- **Expected:** Reading counted under `2026-06-25` (16:30 local), not `06/26`.
- **Result:** **PASS** — both steps readings fell on `2026-06-25`.

### TC-3 — Distance meters→km conversion
- **Requirement:** FR-7 (Partial)
- **Preconditions:** Distance values `8.8` + `6.8` (= 15.6) in one day.
- **Steps:** Run activities conversion.
- **Expected:** `15.6 / 1000 = 0.0156`, rounded to `0.02`.
- **Result:** **PASS** for the arithmetic. *Caveat:* the meters assumption itself
  is unverified (NFR-10).

### TC-4 — Calorie summation/rounding
- **Requirement:** FR-5
- **Preconditions:** Two calorie readings of `500.31`.
- **Steps:** Run activities conversion.
- **Expected:** `1000.62` rounds to `1001`.
- **Result:** **PASS** — `Calories Burned = 1001`.

### TC-5 — Missing-metric defaulting & Activity Calories fallback
- **Requirement:** FR-8
- **Preconditions:** No `Minutes *` or `Activity Calories` folders present.
- **Steps:** Run activities conversion.
- **Expected:** Warnings printed; all `Minutes *` columns `0`;
  `Activity Calories` equals `Calories Burned` (1001).
- **Result:** **PASS** — columns `0`; `Activity Calories = 1001`.

### TC-6 — Per-year Garmin output format
- **Requirement:** FR-9
- **Preconditions:** 2026 data.
- **Steps:** Inspect `out/Activities_2026.csv`.
- **Expected:** First line `Activities`; second line the column header; data rows
  quoted.
- **Result:** **PASS** — exact format produced.

### TC-7 — Weight conversion happy path
- **Requirement:** FR-12, FR-13, FR-14, FR-15, FR-16
- **Preconditions:** CSV rows `2020-07-20T06:59:59Z,59421,API` and
  `2026-05-25T14:39:06.744Z,63320,Aria`.
- **Steps:** `python3 fitbit_convert_weight_to_garmin.py weight_in.csv weight_out.csv`
- **Expected:** `Body` header; `7/20/2020,59.42,0,0`; `5/25/2026,63.32,0,0`
  (fractional seconds handled).
- **Result:** **PASS** — output matched exactly.

### TC-8 — Activities argument validation
- **Requirement:** FR-11
- **Steps:** Run with `--timezone Not/AZone`; separately run with a missing
  export directory.
- **Expected:** Explanatory error on stdout; exit code `1` in both cases.
- **Result:** **PASS** — exit `1` with clear messages.

### TC-9 — Weight argument validation
- **Requirement:** FR-17
- **Steps:** Run with only one argument.
- **Expected:** Usage message; exit code `1`.
- **Result:** **PASS**.

## Security tests

### TC-SEC-1 — No network / credential use
- **Requirement:** NFR-6
- **Steps:** Review imports and runtime behaviour; run offline.
- **Expected:** No socket/HTTP libraries used; runs fully offline; reads only
  user-specified local paths.
- **Result:** **PASS** — only `argparse`, `csv`, `json`, `re`, `sys`,
  `datetime`, `pathlib`, `zoneinfo` imported; no network access.

## Performance tests

### TC-PERF-1 — Conversion latency
- **Requirement:** NFR-2
- **Steps:** Run activities conversion on the sample fixture.
- **Expected:** Completes in under a second.
- **Result:** **PASS** — sub-second on the synthetic fixture; memory bounded by
  per-day aggregation.

## Not executed here

- **End-to-end import into Garmin Connect** — requires a live Garmin account and
  manual upload; out of scope for automated/local testing. Users should verify a
  known day after importing (see README "Known limitations").
