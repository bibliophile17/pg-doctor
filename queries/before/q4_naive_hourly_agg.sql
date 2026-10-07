SELECT time_bucket('1 hour', time) AS bucket, site, avg(temperature) AS avg_temp
FROM sensor_readings
WHERE time > now() - interval '7 days'
GROUP BY bucket, site ORDER BY bucket
