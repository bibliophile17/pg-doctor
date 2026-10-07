# Query review: q4_naive_hourly_agg

## Summary

Your query took **1,139.6 ms** to run (planning: 0.5 ms). 
We found **1 thing** that can be improved.

```sql
SELECT time_bucket('1 hour', time) AS bucket, site, avg(temperature) AS avg_temp
FROM sensor_readings
WHERE time > now() - interval '7 days'
GROUP BY bucket, site ORDER BY bucket
```

## 1. The same summary is recalculated from raw data every time  _(priority: medium)_

**What is happening**

This query summarised 722,470 raw rows into time buckets. If you run it often, the database repeats that work each time. A continuous aggregate keeps the summary pre-calculated and up to date in the background, so reads become tiny.

**What we recommend**

Create a continuous aggregate over the same bucket and query it instead.

```sql
CREATE MATERIALIZED VIEW <name>_hourly WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket, <group_cols>, avg(<value>) AS avg_value
FROM sensor_readings GROUP BY bucket, <group_cols> WITH NO DATA;
```

<details><summary>Supporting numbers</summary>

- raw rows scanned: 722,470

</details>

## What to expect

After applying these changes, re-run the query and send us the new timing. If it is still slower than you need, send the new `EXPLAIN (ANALYZE, BUFFERS)` output and we will take another look.
