SELECT count(*), avg(temperature) FROM sensor_readings
WHERE date_trunc('day', time) = date_trunc('day', now() - interval '2 days')
