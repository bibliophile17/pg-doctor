SELECT bucket, site, avg_temp FROM sensor_hourly
WHERE bucket > now() - interval '7 days'
ORDER BY bucket
