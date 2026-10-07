# PG Doctor

A small tool that takes a slow PostgreSQL / TimescaleDB query, runs `EXPLAIN (ANALYZE, BUFFERS)`, flags what is wrong, and writes a **plain-language, customer-facing report**. It automates the first pass of what a Database Support Engineer does by hand. The repo also documents the same workflow as five support-ticket case studies.

Everything runs on free tools: a Tiger Cloud free service (or local Docker with the open-source TimescaleDB image), Python (standard library plus `psycopg2-binary`) and GitHub Actions.

## Results

Four deliberately seeded problems on a synthetic IoT data set (720,050 rows, 50 devices, 5 days). Times are server-side execution times from single `EXPLAIN ANALYZE` runs.

| Ticket                                                 | Problem                                                              | Before (ms) | After (ms) | Chunks scanned |
| ------------------------------------------------------ | -------------------------------------------------------------------- | ----------: | ---------: | -------------- |
| [1](case_studies/01_device_lookup_slow.md)             | Device lookup felt slow (server was already fast; delay was network) |         1.5 |        0.1 | 4 / 4          |
| [2](case_studies/02_average_never_finishes.md)         | Unbounded query, no time range                                       |        33.8 |        0.8 | 6 / 2          |
| [3](case_studies/03_date_trunc_kills_chunk_pruning.md) | `date_trunc()` on the time column blocks chunk exclusion             |     1,132.6 |       66.8 | 6 / 1          |
| [4](case_studies/04_hourly_report_recomputed.md)       | Hourly rollup recomputed from raw data                               |     1,139.6 |        0.8 | 6 / 2          |
| [5](case_studies/05_anomaly_detection_plpgsql.md)      | Bonus: rolling anomaly detection in PL/pgSQL                         |         n/a |        n/a | n/a            |

Full output: `results/server_side.md`. Saved before/after plans are in `results/plans/`.

**Limitations.** These are single runs on a 720k-row data set on a free service, so absolute numbers will differ at scale; the direction of each improvement is what the case studies show. Client-side timings in `results/benchmark.md` include network round trips to the cloud database and should not be read as query speed.

## What it detects

| Rule                 | Meaning                                                                                |
| -------------------- | -------------------------------------------------------------------------------------- |
| `INEFFICIENT_FILTER` | A scan discards more than 90% of the rows it reads; suggests an index                  |
| `NO_CHUNK_EXCLUSION` | Many chunks scanned: no time range, or a function wrapped around `time`                |
| `HIGH_BUFFER_READS`  | Most blocks came from disk                                                             |
| `NAIVE_AGGREGATE`    | A large `time_bucket` rollup recomputed from raw data; suggests a continuous aggregate |
| `SORT_SPILL`         | A sort spilled to disk                                                                 |
| `BAD_ROW_ESTIMATE`   | Planner estimate off by 100x or more; suggests `ANALYZE`                               |

Each finding becomes a short report section: what is happening (in plain language), what to do, a SQL fix where one applies, and the supporting numbers.

## Quick start (no Docker): Tiger Cloud free service

1. Create a free service at console.cloud.timescale.com and copy its connection string.
2. Set up Python:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. Set the connection string for this terminal only. Never commit it:
   ```powershell
   $env:PGDOCTOR_DSN = "postgres://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require"
   ```
4. Run the pipeline step by step (all SQL runs through `scripts/run_sql.py`, so `psql` is not needed):
   ```powershell
   python scripts/run_sql.py sql/01_schema.sql
   python scripts/run_sql.py sql/02_seed_data.sql --days 5 --devices 50
   python scripts/benchmark.py --dir queries/before --label before
   python scripts/run_sql.py sql/03_fixes.sql
   python scripts/run_sql.py sql/04_anomaly.sql
   python scripts/benchmark.py --dir queries/after --label after
   python scripts/plan_times.py
   ```
5. Generate the "before" reports from the saved plans:
   ```powershell
   Get-ChildItem queries/before/*.sql | ForEach-Object { python -m pgdoctor diagnose --file $_.FullName --plan-json "results/plans/before/$($_.BaseName).json" --out-dir reports/before | Out-Null }
   ```

## Try it offline (no database)

```bash
python -m pgdoctor diagnose --file examples/sample_query.sql --plan-json examples/sample_plan.json
python -m unittest discover -s tests -v
```

## Optional: local Docker

`docker compose up -d` starts a local TimescaleDB (`docker-compose.yml`); then use the same scripts with the default connection string. `scripts/run_all.sh` automates the whole run.

## Layout

- `pgdoctor/`: plan parser, diagnostic rules, report writer, CLI
- `sql/`: schema, seed data, fixes, PL/pgSQL anomaly detection
- `queries/before|after/`: the seeded problem queries and their fixes
- `scripts/`: SQL runner, benchmark, server-side timing summary
- `case_studies/`: five ticket-style write-ups (symptom, investigation, root cause, fix, customer explanation)
- `reports/before/`: example generated customer reports
- `tests/`: unit tests for the parser and rules (no database required)

## Safety

`EXPLAIN ANALYZE` executes the query, so the tool accepts only `SELECT`/`WITH` statements, in a read-only transaction with a timeout. The rules are heuristics with thresholds you can tune in `pgdoctor/rules.py`.
