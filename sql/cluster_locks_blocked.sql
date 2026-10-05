-- measurement: pg_locks_blocked | scope: cluster | interval: 15s
-- tags: datname
-- One row per database (zeros included, so time series have no gaps).
WITH w AS (
    SELECT a.datname,
           a.pid,
           pg_blocking_pids(a.pid)                                  AS blockers,
           extract(epoch FROM clock_timestamp() - a.state_change)   AS wait_s
    FROM pg_stat_activity a
    WHERE a.wait_event_type = 'Lock'
)
SELECT
    d.datname,
    count(w.pid) FILTER (WHERE cardinality(w.blockers) > 0)         AS blocked,
    (SELECT count(DISTINCT x)
       FROM w w2 CROSS JOIN LATERAL unnest(w2.blockers) AS x
      WHERE w2.datname = d.datname)                                 AS blocking,
    coalesce(max(w.wait_s), 0)::float8                              AS max_wait_s
FROM pg_database d
    LEFT JOIN w ON w.datname = d.datname
WHERE d.datallowconn
  AND NOT d.datistemplate
  AND d.datname NOT IN ('rdsadmin')
GROUP BY d.datname;
