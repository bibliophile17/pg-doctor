SELECT count(*), avg(temperature) FROM sensor_readings
WHERE time >= date_trunc('day', now() - interval '2 days')
  AND time <  date_trunc('day', now() - interval '2 days') + interval '1 day'
