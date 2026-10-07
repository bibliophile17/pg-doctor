# Ticket 2: "Average temperature for a device gets slower every week"

**Reported symptom:** `SELECT avg(temperature) FROM sensor_readings WHERE device_id = 42` takes longer as the table grows.

## Investigation

1. `python -m pgdoctor diagnose --file queries/before/q2_no_time_filter.sql`
2. The plan scans every chunk (6 of 6) because the query has no time range, and filters by `device_id` inside each one.

## Root cause

With no time bound, the cost of the query grows with the entire history of the table, so it gets slower every day that new data arrives.

## Fix

- Add a time range that matches the real question (`queries/after/q2_no_time_filter.sql`, last 24 hours).
- The `(device_id, time DESC)` index from `sql/03_fixes.sql` makes each remaining chunk cheap to search.

## Evidence

- Server-side execution time: 33.8 ms before, 0.8 ms after.
- Chunks scanned: 6 before, 2 after.
- Two changes contributed: the added time range (the main reason the chunk count dropped) and the index. They were applied together, so the gain cannot be split between them.
- Data set: 720,050 rows, 5 days. The gap widens as history accumulates.

## Customer-facing explanation

The database was reading your entire history every time, so it slowed down as your data grew. If you only need recent behaviour, adding a time window lets it ignore old data completely. If you need all-time averages, let us know and we can set up a pre-computed summary for that instead.
