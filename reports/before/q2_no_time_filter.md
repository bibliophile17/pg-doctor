# Query review: q2_no_time_filter

## Summary

Your query took **33.8 ms** to run (planning: 0.2 ms). 
We found **1 thing** that can be improved.

```sql
SELECT avg(temperature) FROM sensor_readings WHERE device_id = 42
```

## 1. The database reads far more rows than it needs  _(priority: high)_

**What is happening**

To answer your query, the database looked at 720,050 rows and threw away 705,649 of them (98.0%), keeping only 14,401. It is like finding one person's name by reading every page of a phone book, instead of using the index at the back. An index on the column(s) you filter by lets the database jump straight to the matching rows.

**What we recommend**

Create an index on (device_id, time DESC). On a large, busy table, use the per-chunk option so writes are not blocked for long.

```sql
CREATE INDEX idx_sensor_readings_device_id_time ON sensor_readings (device_id, time DESC)
  WITH (timescaledb.transaction_per_chunk);
```

<details><summary>Supporting numbers</summary>

- rows examined: 720,050
- rows discarded: 705,649
- filter columns: device_id

</details>

## What to expect

After applying these changes, re-run the query and send us the new timing. If it is still slower than you need, send the new `EXPLAIN (ANALYZE, BUFFERS)` output and we will take another look.
