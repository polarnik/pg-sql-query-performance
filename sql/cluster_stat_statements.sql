-- pg_stat_statements (classic boards pgquery/pgstat): top-500 statements by total_exec_time.
-- Scope: cluster (maintenance DB). Text is a field (query_short, query_mask_short), never a tag.
SELECT
    coalesce(r.rolname, s.userid::text) AS usename,
    coalesce(d.datname, s.dbid::text) AS datname,
    s.queryid::text AS queryid,
    s.toplevel::text AS toplevel,
    md5(s.query)::uuid::varchar(100) AS query_md5,
    md5(m.query_mask)::uuid::varchar(100) AS query_mask_md5,
    left(regexp_replace(s.query, '\s+', ' ', 'g'), 120) AS query_short,
    left(m.query_mask, 120) AS query_mask_short,
    s.calls,
    s.total_exec_time,
    s.rows,
    s.shared_blks_hit,
    s.shared_blks_read,
    s.shared_blks_dirtied,
    s.shared_blks_written,
    s.temp_blks_read,
    s.temp_blks_written
FROM pg_stat_statements s
    LEFT JOIN pg_roles r ON r.oid = s.userid
    LEFT JOIN pg_database d ON d.oid = s.dbid
    CROSS JOIN LATERAL (
        SELECT regexp_replace(
                   regexp_replace(
                       regexp_replace(s.query, '\s+', ' ', 'g'),
                       '\$[0-9]+', '$0', 'g'),
                   '\(\$0,[^)]+\)', '($0,$0)', 'g') AS query_mask
    ) m
WHERE coalesce(r.rolname, '') NOT IN ('rdsadmin', 'rdsrepladmin')
ORDER BY s.total_exec_time DESC
LIMIT 500
