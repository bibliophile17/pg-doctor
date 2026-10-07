-- Rolling z-score anomaly detection (PL/pgSQL), per device.
CREATE OR REPLACE FUNCTION detect_anomalies(
    p_device_id integer,
    p_from      timestamptz,
    p_to        timestamptz,
    p_window    integer DEFAULT 60,
    p_z         numeric DEFAULT 4
) RETURNS TABLE (ts timestamptz, temperature double precision, z_score double precision)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    IF p_from >= p_to THEN
        RAISE EXCEPTION 'p_from (%) must be earlier than p_to (%)', p_from, p_to;
    END IF;
    RETURN QUERY
    WITH w AS (
        SELECT r.time AS t, r.temperature AS temp,
               avg(r.temperature)         OVER win AS mu,
               stddev_samp(r.temperature) OVER win AS sd
        FROM sensor_readings r
        WHERE r.device_id = p_device_id AND r.time >= p_from AND r.time < p_to
        WINDOW win AS (ORDER BY r.time ROWS BETWEEN p_window PRECEDING AND 1 PRECEDING)
    )
    SELECT t, temp, (temp - mu) / NULLIF(sd, 0)
    FROM w
    WHERE sd IS NOT NULL AND abs((temp - mu) / NULLIF(sd, 0)) >= p_z
    ORDER BY t;
END $$;

CREATE TABLE IF NOT EXISTS sensor_anomalies (
    device_id integer, ts timestamptz, temperature double precision,
    z_score double precision, detected_at timestamptz DEFAULT now(),
    PRIMARY KEY (device_id, ts)
);

-- Procedure: scan the last N hours for every device and persist new anomalies.
CREATE OR REPLACE PROCEDURE record_anomalies(p_hours integer DEFAULT 24)
LANGUAGE plpgsql AS $$
DECLARE d integer; n_total bigint := 0; n bigint;
BEGIN
    FOR d IN SELECT DISTINCT device_id FROM sensor_readings
             WHERE time > now() - make_interval(hours => p_hours) LOOP
        INSERT INTO sensor_anomalies (device_id, ts, temperature, z_score)
        SELECT d, a.ts, a.temperature, a.z_score
        FROM detect_anomalies(d, now() - make_interval(hours => p_hours), now()) a
        ON CONFLICT DO NOTHING;
        GET DIAGNOSTICS n = ROW_COUNT;
        n_total := n_total + n;
    END LOOP;
    RAISE NOTICE 'record_anomalies: % new anomalies', n_total;
END $$;
