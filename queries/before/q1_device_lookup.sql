SELECT * FROM sensor_readings
WHERE device_id = 42 AND time > now() - interval '3 days'
ORDER BY time DESC LIMIT 100
