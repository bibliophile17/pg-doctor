-- Default ~2M rows: {{DAYS}} days x 30s interval x {{DEVICES}} devices.
-- Run: python scripts/run_sql.py sql/02_seed_data.sql --days 7 --devices 100
INSERT INTO sensor_readings (time, device_id, site, temperature, humidity, battery)
SELECT t, d, 'site-' || (d % 20),
       20 + 5 * sin(extract(epoch FROM t) / 86400 * 2 * pi()) + random() * 2,
       40 + random() * 20,
       100 - random() * 50
FROM generate_series(now() - interval '{{DAYS}} days', now(), interval '30 seconds') AS t,
     generate_series(1, {{DEVICES}}) AS d;

-- Inject a few obvious spikes so the anomaly function has something to find.
UPDATE sensor_readings SET temperature = temperature + 25
WHERE device_id = 42 AND time > now() - interval '1 day' AND random() < 0.0005;

ANALYZE sensor_readings;
