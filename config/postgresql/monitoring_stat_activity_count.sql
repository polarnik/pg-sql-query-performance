DROP FUNCTION IF EXISTS public.monitoring_stat_activity_count();

CREATE OR REPLACE FUNCTION public.monitoring_stat_activity_count()
RETURNS TABLE (
    usename name, 
    datname name, 
    state text, 
    wait_event text, 
    wait_event_type text, 
    backend_type text, 
    "count" bigint,
    sum_state_seconds double precision, 
    max_state_seconds double precision,
    avg_state_seconds double precision,
    sum_connection_seconds double precision, 
    max_connection_seconds double precision,
    avg_connection_seconds double precision
)
AS $$
SELECT
    coalesce(usename, '(none)') as usename,
    coalesce(datname, '(none)') as datname,
    state, 
    count(*) as "count",
    coalesce(sum(extract(epoch FROM clock_timestamp() - state_change)),0) as sum_state_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - state_change)),0) as max_state_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - state_change)),0) as avg_state_seconds,
    coalesce(sum(extract(epoch FROM clock_timestamp() - backend_start)),0) as sum_connection_seconds,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)),0) as max_connection_seconds,
    coalesce(avg(extract(epoch FROM clock_timestamp() - backend_start)),0) as avg_connection_seconds
FROM pg_stat_activity
WHERE state IS NOT NULL
GROUP BY usename , datname, state, wait_event, wait_event_type, backend_type
;
$$
LANGUAGE SQL SECURITY DEFINER;