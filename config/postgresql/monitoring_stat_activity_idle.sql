DROP FUNCTION IF EXISTS public.monitoring_stat_activity_idle();

CREATE OR REPLACE FUNCTION public.monitoring_stat_activity_idle()
RETURNS TABLE(
    usename name,
    datname name,
    state text,
    query_md5 character varying,
    query character varying,
    count bigint,
    sum_idle_seconds double precision,
    max_idle_seconds double precision,
    avg_idle_seconds double precision,
    max_connection_seconds double precision,
    avg_connection_seconds double precision
)
LANGUAGE sql
SECURITY DEFINER
AS $function$
SELECT
    usename,
    datname,
    state,
    md5(query)::uuid::varchar(100) as query_md5,
    left(regexp_replace(query, '\\r|\\n|\\t|\\s+', ' ', 'g'), 10000) query,
    count(*) as "count",
    coalesce(sum(extract(epoch FROM clock_timestamp() - state_change)),0) as sum_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - state_change)),0) as max_idle_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - state_change)),0) as avg_idle_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)),0) as max_connection_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - backend_start)),0) as avg_connection_seconds
FROM pg_stat_activity
WHERE state = 'idle'
GROUP BY usename , datname, state, md5(query)::uuid::varchar(100), query;
$function$
;