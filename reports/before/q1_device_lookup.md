# Query review: q1_device_lookup

## Summary

Your query took **1.5 ms** to run (planning: 0.4 ms). 
We found **1 thing** that can be improved.

```sql
SELECT * FROM sensor_readings
WHERE device_id = 42 AND time > now() - interval '3 days'
ORDER BY time DESC LIMIT 100
```

## 1. The planner's guess about row counts was far off  _(priority: low)_

**What is happening**

At a 'Index Scan' step the database expected 2,827 rows but found 0. Wrong guesses can lead it to choose a slower plan.

**What we recommend**

Refresh statistics with ANALYZE on the table, then re-check the plan.

```sql
ANALYZE sensor_readings;
```

<details><summary>Supporting numbers</summary>

- expected rows: 2,827
- actual rows: 0

</details>

## What to expect

After applying these changes, re-run the query and send us the new timing. If it is still slower than you need, send the new `EXPLAIN (ANALYZE, BUFFERS)` output and we will take another look.
