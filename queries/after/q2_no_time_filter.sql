SELECT avg(temperature) FROM sensor_readings
WHERE device_id = 42 AND time > now() - interval '24 hours'
