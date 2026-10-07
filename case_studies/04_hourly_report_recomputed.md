# Ticket 4: "Our hourly averages report is slow and runs every minute"

**Reported symptom:** A report grouping by `time_bucket('1 hour')` and `site` over 7 days is slow and puts load on the database.

## Investigation

1. `python -m pgdoctor diagnose --file queries/before/q4_naive_hourly_agg.sql`
2. PG Doctor flags `NAIVE_AGGREGATE`: every run re-summarises raw rows across all 6 chunks.

## Root cause

The same summary is recalculated from raw data on every run, even though the underlying readings rarely change after they arrive.

## Fix

- Create a continuous aggregate, `sensor_hourly`, with a refresh policy (`sql/03_fixes.sql`).
- Point the report at it (`queries/after/q4_naive_hourly_agg.sql`).

## Evidence

- Server-side execution time: 1,139.6 ms before, 0.8 ms after (more than 1,000x faster).
- The "after" plan reads 2 chunks of the materialized hypertable instead of the raw data.
- The work moves to a background refresh job (every 30 minutes) instead of being paid on every report.
- Data set: 720,050 rows, 5 days. The raw-data cost grows with table size; the aggregate stays small.

## Customer-facing explanation

Instead of adding up every reading each time you open the report, the database now keeps the hourly totals ready and updates them in the background. Your report reads a small summary instead of the full history, so it is almost instant.
