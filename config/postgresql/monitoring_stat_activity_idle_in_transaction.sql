DROP FUNCTION IF EXISTS public.monitoring_stat_activity_idle_in_transaction() ;
 
CREATE OR REPLACE FUNCTION public.monitoring_stat_activity_idle_in_transaction()
RETURNS TABLE (
    usename name,
    datname name,
    state text,
    query_md5 varchar(100),
    query varchar(10000),
    "count" bigint,
    sum_idle_seconds double precision,
    max_idle_seconds double precision,
    avg_idle_seconds double precision,
    max_connection_seconds double precision,
    avg_connection_seconds double precision
)
AS $$
SELECT
    usename,
    datname,
    state,
    md5(query)::uuid::varchar(100) as query_md5,
    left(regexp_replace(query, '\\r|\\n|\\t|\\s+', ' ', 'g'), 10000) query,
    count(*) as "count",
    coalesce(sum(extract(epoch FROM clock_timestamp() - xact_start)),0) as sum_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - xact_start)),0) as max_idle_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - xact_start)),0) as avg_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)),0) as max_connection_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - backend_start)),0) as avg_connection_seconds
FROM pg_stat_activity
WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
GROUP BY usename , datname, state, md5(query)::uuid::varchar(100), query;
$$
LANGUAGE SQL SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.monitoring_stat_activity_idle_in_transaction() TO telegraf_monitoring_user;