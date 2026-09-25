-- pg_stat_activity_count (classic board pgActivity), was public.monitoring_stat_activity_count().
-- Scope: cluster (maintenance DB).
SELECT
    coalesce(usename, '(none)') AS usename,
    coalesce(datname, '(none)') AS datname,
    state,
    coalesce(wait_event, '(none)') AS wait_event,
    coalesce(wait_event_type, '(none)') AS wait_event_type,
    backend_type,
    count(*) AS "count",
    coalesce(sum(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8 AS sum_state_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8 AS max_state_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8 AS avg_state_seconds,
    coalesce(sum(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS sum_connection_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS max_connection_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS avg_connection_seconds
FROM pg_stat_activity
WHERE state IS NOT NULL
GROUP BY 1, 2, 3, 4, 5, 6
