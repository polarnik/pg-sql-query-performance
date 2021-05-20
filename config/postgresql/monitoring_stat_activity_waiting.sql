DROP FUNCTION IF EXISTS public.monitoring_stat_activity_waiting();

CREATE OR REPLACE FUNCTION public.monitoring_stat_activity_waiting()
RETURNS TABLE (usename name, datname name, state text, query_md5 varchar(100), query varchar(10000), "count" bigint, max_idle_seconds double precision, avg_idle_seconds double precision)
AS $$
SELECT
  usename,
  datname,
  state,
  md5(query)::uuid::varchar(100) as query_md5,
  left(regexp_replace(query, '\\r|\\n|\\t|\\s+', ' ', 'g'), 10000) query,
  count(*),
  coalesce(max(extract(epoch FROM clock_timestamp() - state_change)),0) as max_idle_seconds,
  coalesce(avg(extract(epoch FROM clock_timestamp() - state_change)),0) as avg_idle_seconds
FROM pg_stat_activity
where state IN ('Lock')
group by usename , datname, state, md5(query)::uuid::varchar(100), query;
$$
LANGUAGE SQL SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.monitoring_stat_activity_waiting() TO telegraf_monitoring_user;