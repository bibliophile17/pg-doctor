-- Fixes for the seeded problems. Run AFTER recording the "before" benchmark.

-- Problem 1 & 2: filtering on device_id with no supporting index.
CREATE INDEX IF NOT EXISTS idx_sensor_device_time ON sensor_readings (device_id, time DESC);

-- Problem 4: naive hourly aggregation -> continuous aggregate.
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       site,
       avg(temperature) AS avg_temp,
       max(temperature) AS max_temp,
       count(*)         AS n
FROM sensor_readings
GROUP BY bucket, site
WITH NO DATA;

CALL refresh_continuous_aggregate('sensor_hourly', now() - interval '8 days', now());

SELECT add_continuous_aggregate_policy('sensor_hourly',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes', if_not_exists => true);

-- Storage: compression. (Older-style settings; newer Timescale versions call this
-- "columnstore" but these options still work.)
ALTER TABLE sensor_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby   = 'time DESC'
);
SELECT add_compression_policy('sensor_readings', INTERVAL '2 days', if_not_exists => true);
