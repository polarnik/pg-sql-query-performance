-- measurement: pg_role_limits | scope: cluster | interval: 30s
-- tags: rolname
-- rolconnlimit = -1 means "unlimited" -> effective_conn_limit falls back to the server limit.
WITH l AS (
    SELECT current_setting('max_connections')::int
         - current_setting('superuser_reserved_connections')::int
         - current_setting('reserved_connections')::int AS server_limit
), a AS (
    SELECT usesysid, count(*) AS current
    FROM pg_stat_activity
    WHERE backend_type = 'client backend'
    GROUP BY usesysid
)
SELECT
    r.rolname,
    r.rolconnlimit,
    CASE WHEN r.rolconnlimit = -1 THEN l.server_limit
         ELSE least(r.rolconnlimit, l.server_limit) END            AS effective_conn_limit,
    coalesce(a.current, 0)                                          AS current,
    round(100.0 * coalesce(a.current, 0)
          / nullif(CASE WHEN r.rolconnlimit = -1 THEN l.server_limit
                        ELSE least(r.rolconnlimit, l.server_limit) END, 0), 2)::float8 AS usage_pct
FROM pg_roles r
    CROSS JOIN l
    LEFT JOIN a ON a.usesysid = r.oid
WHERE r.rolcanlogin
  AND r.rolname NOT IN ('rdsadmin', 'rdsrepladmin');
