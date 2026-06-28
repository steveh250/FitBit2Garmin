# Deployment & Setup

> **Scope note.** The build standard's deployment target (Vercel + SvelteKit +
> PostgreSQL + Edge Middleware) does not apply here. FitBit2Garmin has **no
> server, no hosted environment, and no database**, so there is nothing to
> "deploy" in the hosting sense. "Deployment" for this project means *obtaining
> the scripts and running them locally*. The Vercel, database-migration, and
> edge-middleware sections required by the standard are documented as **Not
> Applicable** with rationale at the end.

## Prerequisites

| Component | Required version | Notes |
| --- | --- | --- |
| Python | **3.9+** | Needs the stdlib `zoneinfo` module (added in 3.9). Verified on 3.11. |
| pip / virtualenv | not required | No third-party dependencies to install. |
| OS tz database | recommended | On minimal Linux images install `tzdata` so `zoneinfo` can resolve IANA names. |
| Node / Vercel CLI / PostgreSQL | **N/A** | Not used by this project. |

## Environment variable reference

This project reads **no environment variables**. All configuration is passed as
command-line arguments.

| Variable | Description | Example | Required |
| --- | --- | --- | --- |
| *(none)* | No env vars are consulted by either script | — | — |

The only runtime input that resembles configuration is the activities script's
`--timezone` flag (an IANA name, default `America/Vancouver`).

## Setup (first time)

```bash
git clone https://github.com/steveh250/FitBit2Garmin.git
cd FitBit2Garmin
python3 --version   # confirm >= 3.9
```

No install, build, or compile step is needed.

## Running

```bash
# Activities: scan an export folder, write per-year Garmin CSVs into ./out
python3 fitbit_activities_to_garmin.py /path/to/export_folder ./out [--timezone Area/City]

# Weight: convert a single Fitbit weight CSV to a Garmin Body CSV
python3 fitbit_convert_weight_to_garmin.py weight_export.csv weight_out.csv
```

Exit code `0` means success; `1` means a fatal input error (bad arguments,
unknown timezone, or a missing export directory) — the message explains which.

## Subsequent runs / "redeploy"

Pull the latest scripts and re-run:

```bash
git pull origin main
python3 fitbit_activities_to_garmin.py /path/to/export_folder ./out
```

There is no cache, state, or service to restart.

## Local development that mirrors production

Because the scripts run identically everywhere (no server, no env-specific
behaviour), local development *is* production behaviour. To iterate safely:

1. Assemble a small synthetic export folder (a couple of metric folders with one
   JSON and one CSV file each) and a tiny weight CSV.
2. Run the scripts against that fixture and inspect the generated CSVs.
3. Spot-check a known day's totals against the Fitbit app before trusting real
   output (especially Distance — its unit is an unconfirmed assumption).

## Rollback procedure

Roll back by checking out a previous revision of the scripts; outputs are
regenerated from source data each run, so there is no migration to reverse:

```bash
git log --oneline             # find the last-good commit
git checkout <commit> -- fitbit_activities_to_garmin.py fitbit_convert_weight_to_garmin.py
# re-run the scripts to regenerate CSVs
```

If a generated CSV is wrong, simply delete it and re-run after fixing the input
or reverting the script — nothing downstream persists.

## Not Applicable (with rationale)

| Standard requirement | Status | Rationale |
| --- | --- | --- |
| Step-by-step Vercel deploy | N/A | No web frontend/API; nothing is hosted. |
| Database migration procedure | N/A | No database exists. |
| Vercel Edge Middleware auth header injection | N/A | No middleware, no auth, no HTTP layer. |
