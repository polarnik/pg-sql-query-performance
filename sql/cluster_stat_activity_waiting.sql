-- pg_stat_activity_waiting (classic board pgActivity), was public.monitoring_stat_activity_waiting().
-- state 'Lock' never existed, lock waits are wait_event_type = 'Lock'. Scope: cluster (maintenance DB).
SELECT
    coalesce(usename, '(none)') AS usename,
    coalesce(datname, '(none)') AS datname,
    state,
    coalesce(wait_event, '(none)') AS wait_event,
    md5(query)::uuid::varchar(100) AS query_md5,
    left(regexp_replace(min(query), '\s+', ' ', 'g'), 120) AS query_short,
    count(*) AS "count",
    coalesce(max(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8 AS max_idle_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8 AS avg_idle_seconds
FROM pg_stat_activity
WHERE wait_event_type = 'Lock'
GROUP BY 1, 2, 3, 4, 5
