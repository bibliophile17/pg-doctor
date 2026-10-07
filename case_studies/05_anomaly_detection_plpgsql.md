# Case 5 (bonus): rolling anomaly detection in PL/pgSQL

**Customer need:** "Alert me when a sensor reading looks wildly different from that device's recent behaviour."

## What was built (`sql/04_anomaly.sql`)

- `detect_anomalies(device_id, from, to, window, z)`: computes a rolling mean and standard deviation over the previous `window` readings using window functions, and returns readings whose z-score exceeds the threshold. It validates its time range and uses `NULLIF` to avoid dividing by zero on flat signals.
- `record_anomalies(hours)`: a procedure that loops over devices active in the last N hours and stores new anomalies in `sensor_anomalies`. `ON CONFLICT DO NOTHING` keeps reruns safe.

## Try it

```sql
SELECT * FROM detect_anomalies(42, now() - interval '1 day', now());
CALL record_anomalies(24);
```

## Design notes

- Found and fixed a false positive: the first version scored readings before a full window of history
  existed, so a z-score computed from only a few points (tiny standard deviation) flagged a normal
  reading with z = -30.6. The function now scores a reading only after p_window earlier readings exist.
  Callers should therefore request a range that starts at least p_window readings before the period of interest.

## Customer-facing explanation

This check compares each reading with the device's own recent history and flags the ones that stand out. You can tune how sensitive it is with the window size and the threshold.
