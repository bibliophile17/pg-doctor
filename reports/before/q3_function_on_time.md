# Query review: q3_function_on_time

## Summary

Your query took **1,132.6 ms** to run (planning: 0.2 ms). 
We found **2 things** that can be improved.

```sql
SELECT count(*), avg(temperature) FROM sensor_readings
WHERE date_trunc('day', time) = date_trunc('day', now() - interval '2 days')
```

## 1. The database reads far more rows than it needs  _(priority: high)_

**What is happening**

To answer your query, the database looked at 576,050 rows and threw away 576,050 of them (100.0%), keeping only 0. It is like finding one person's name by reading every page of a phone book, instead of using the index at the back. An index on the column(s) you filter by lets the database jump straight to the matching rows.

**What we recommend**

Create an index on (<filter_columns>, time DESC). On a large, busy table, use the per-chunk option so writes are not blocked for long.

```sql
CREATE INDEX idx_sensor_readings_cols_time ON sensor_readings (<filter_columns>, time DESC)
  WITH (timescaledb.transaction_per_chunk);
```

<details><summary>Supporting numbers</summary>

- rows examined: 576,050
- rows discarded: 576,050
- filter columns: <filter_columns>

</details>

## 2. The planner's guess about row counts was far off  _(priority: low)_

**What is happening**

At a 'Seq Scan' step the database expected 720 rows but found 144,000. Wrong guesses can lead it to choose a slower plan.

**What we recommend**

Refresh statistics with ANALYZE on the table, then re-check the plan.

```sql
ANALYZE sensor_readings;
```

<details><summary>Supporting numbers</summary>

- expected rows: 720
- actual rows: 144,000

</details>

## What to expect

After applying these changes, re-run the query and send us the new timing. If it is still slower than you need, send the new `EXPLAIN (ANALYZE, BUFFERS)` output and we will take another look.
