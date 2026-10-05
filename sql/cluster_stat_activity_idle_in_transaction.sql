-- pg_stat_activity_idle_in_transaction (classic board pgActivity),
-- was public.monitoring_stat_activity_idle_in_transaction(). Scope: cluster (maintenance DB).
SELECT
    coalesce(usename, '(none)') AS usename,
    coalesce(datname, '(none)') AS datname,
    state,
    md5(query)::uuid::varchar(100) AS query_md5,
    left(regexp_replace(min(query), '\s+', ' ', 'g'), 120) AS query_short,
    count(*) AS "count",
    coalesce(sum(extract(epoch FROM clock_timestamp() - xact_start)), 0)::float8 AS sum_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - xact_start)), 0)::float8 AS max_idle_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - xact_start)), 0)::float8 AS avg_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS max_connection_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS avg_connection_seconds
FROM pg_stat_activity
WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
GROUP BY 1, 2, 3, 4
