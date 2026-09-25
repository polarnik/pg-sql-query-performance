-- measurement: pg_db_limits | scope: cluster | interval: 30s
-- tags: datname
-- datconnlimit = -1 means "unlimited" -> effective_conn_limit falls back to the server limit.
WITH l AS (
    SELECT current_setting('max_connections')::int
         - current_setting('superuser_reserved_connections')::int
         - current_setting('reserved_connections')::int AS server_limit
), a AS (
    SELECT datid, count(*) AS numbackends
    FROM pg_stat_activity
    WHERE backend_type = 'client backend'
    GROUP BY datid
)
SELECT
    d.datname,
    d.datconnlimit,
    CASE WHEN d.datconnlimit = -1 THEN l.server_limit
         ELSE least(d.datconnlimit, l.server_limit) END            AS effective_conn_limit,
    coalesce(a.numbackends, 0)                                      AS numbackends,
    round(100.0 * coalesce(a.numbackends, 0)
          / nullif(CASE WHEN d.datconnlimit = -1 THEN l.server_limit
                        ELSE least(d.datconnlimit, l.server_limit) END, 0), 2)::float8 AS usage_pct
FROM pg_database d
    CROSS JOIN l
    LEFT JOIN a ON a.datid = d.oid
WHERE d.datallowconn
  AND NOT d.datistemplate
  AND d.datname NOT IN ('rdsadmin');
