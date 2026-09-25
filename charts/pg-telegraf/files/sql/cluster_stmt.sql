-- measurement: pg_stmt | scope: cluster (DB with the pg_stat_statements extension) | interval: 5m
-- tags: usename, datname, queryid, toplevel, query_md5, query_mask_md5
-- fields: counters (cumulative) + query_short (<=120 chars)
-- Selection: top 200 by cumulative total_exec_time UNION top 200 by calls.
--   Cumulative ranking is stable, so a statement rarely drops out of the set (no derivative gaps).
-- Mask rules (applied only to the selected rows):
--   1. collapse whitespace; 2. $1..$N -> $0; 3. IN-lists ($0, $0, ...) -> ($0,$0);
--   4. repeated VALUES tuples (...), (...), ... -> (...),...
-- md5 is computed on the FULL mask/query, text is truncated afterwards.
WITH ranked AS (
    SELECT s.*,
           row_number() OVER (ORDER BY s.total_exec_time DESC) AS rn_time,
           row_number() OVER (ORDER BY s.calls DESC)           AS rn_calls
    FROM pg_stat_statements s
), top AS (
    SELECT * FROM ranked WHERE rn_time <= 200 OR rn_calls <= 200
)
SELECT
    coalesce(r.rolname, t.userid::text)                             AS usename,
    coalesce(d.datname, t.dbid::text)                               AS datname,
    t.queryid::text                                                 AS queryid,
    t.toplevel::text                                                AS toplevel,
    md5(t.query)::uuid::varchar(100)                                AS query_md5,
    md5(m.query_mask)::uuid::varchar(100)                           AS query_mask_md5,
    left(regexp_replace(t.query, '\s+', ' ', 'g'), 120)             AS query_short,
    t.calls,
    t.total_exec_time,
    t.plans,
    t.total_plan_time,
    t.rows,
    t.shared_blks_hit,
    t.shared_blks_read,
    t.shared_blks_dirtied,
    t.shared_blks_written,
    t.local_blks_read,
    t.temp_blks_read,
    t.temp_blks_written,
    t.shared_blk_read_time,
    t.shared_blk_write_time,
    t.temp_blk_read_time,
    t.temp_blk_write_time,
    t.wal_bytes::bigint                                             AS wal_bytes,
    coalesce(extract(epoch FROM t.stats_since), 0)::bigint          AS stats_since_epoch
FROM top t
    LEFT JOIN pg_roles r ON r.oid = t.userid
    LEFT JOIN pg_database d ON d.oid = t.dbid
    CROSS JOIN LATERAL (
        SELECT regexp_replace(
                   regexp_replace(
                       regexp_replace(
                           regexp_replace(t.query, '\s+', ' ', 'g'),
                           '\$[0-9]+', '$0', 'g'),
                       '\(\s*\$0(\s*,\s*\$0)+\s*\)', '($0,$0)', 'g'),
                   '(\([$0, ]+\))(\s*,\s*\([$0, ]+\))+', '\1,...', 'g') AS query_mask
    ) m
WHERE coalesce(r.rolname, '') NOT IN ('rdsadmin', 'rdsrepladmin');
