# Ticket 3: "Querying one day of data scans the whole table"

**Reported symptom:** Filtering with `date_trunc('day', time) = ...` is slow even though only one day is requested.

## Investigation

1. `python -m pgdoctor diagnose --file queries/before/q3_function_on_time.sql`
2. PG Doctor reports `NO_CHUNK_EXCLUSION` and notes that a function is applied to the `time` column. The plan opens all 6 chunks.

## Root cause

TimescaleDB skips chunks outside the requested time range, but only when the `time` column is compared directly. Wrapping it in `date_trunc()` hides the range from the planner, so it cannot rule any chunk out.

## Fix

Rewrite the filter as a half-open range on the bare column (`queries/after/q3_function_on_time.sql`):
`time >= date_trunc('day', ...) AND time < date_trunc('day', ...) + interval '1 day'`

## Evidence

- Server-side execution time: 1,132.6 ms before, 66.8 ms after (about 17x faster).
- Chunks scanned: 6 before, 1 after.
- The remaining 66.8 ms is the real work of aggregating one day of data.
- Data set: 720,050 rows, 5 days.

## Customer-facing explanation

Your data is stored in daily boxes. When the query transforms the time value, the database cannot tell which box holds the day you want, so it opens all of them. Comparing the raw time against a start and an end lets it open exactly one box.
