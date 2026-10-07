-- Runs automatically on first container start.
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE sensor_readings (
    time        timestamptz      NOT NULL,
    device_id   integer          NOT NULL,
    site        text             NOT NULL,
    temperature double precision,
    humidity    double precision,
    battery     double precision
);

-- 1-day chunks. NOTE: only the default (time DESC) index exists.
-- There is deliberately NO index on device_id - that is seeded problem #1.
SELECT create_hypertable('sensor_readings', 'time', chunk_time_interval => INTERVAL '1 day');
