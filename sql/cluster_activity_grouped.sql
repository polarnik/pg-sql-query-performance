-- measurement: pg_activity_grouped | scope: cluster | interval: 15s
-- tags: datname, usename, application_name, state, wait_event_type
SELECT
    coalesce(datname, '(none)')                                     AS datname,
    coalesce(usename, '(none)')                                     AS usename,
    coalesce(nullif(left(application_name, 64), ''), '(none)')      AS application_name,
    coalesce(state, '(none)')                                       AS state,
    coalesce(wait_event_type, '(none)')                             AS wait_event_type,
    count(*)                                                        AS cnt,
    coalesce(max(extract(epoch FROM clock_timestamp() - xact_start)), 0)::float8    AS max_xact_age_s,
    coalesce(max(extract(epoch FROM clock_timestamp() - state_change)), 0)::float8  AS max_state_age_s,
    coalesce(max(extract(epoch FROM clock_timestamp() - backend_start)), 0)::float8 AS max_backend_age_s
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND coalesce(usename, '') NOT IN ('rdsadmin', 'rdsrepladmin')
GROUP BY 1, 2, 3, 4, 5;
