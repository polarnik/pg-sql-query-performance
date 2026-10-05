-- measurement: pg_stmt_text | scope: cluster (DB with the pg_stat_statements extension) | interval: 10m
-- tags: query_mask_md5, query_md5, queryid
-- fields: query (<=10000), query_mask (<=10000)
-- Low-frequency md5 -> full text lookup for the Statement Detail dashboard.
-- Same selection as pg_stmt (top 200 by total_exec_time UNION top 200 by calls).
-- One row per (query_md5, queryid): one text can have several queryid (other DB / search_path), and one
-- queryid several texts (whitespace / comments are not part of the queryid).
WITH ranked AS (
    SELECT s.queryid, s.query,
           row_number() OVER (ORDER BY s.total_exec_time DESC) AS rn_time,
           row_number() OVER (ORDER BY s.calls DESC)           AS rn_calls
    FROM pg_stat_statements s
        LEFT JOIN pg_roles r ON r.oid = s.userid
    WHERE coalesce(r.rolname, '') NOT IN ('rdsadmin', 'rdsrepladmin')
), top AS (
    SELECT DISTINCT ON (md5(query), queryid) queryid, query
    FROM ranked
    WHERE rn_time <= 200 OR rn_calls <= 200
)
SELECT
    md5(m.query_mask)::uuid::varchar(100)                           AS query_mask_md5,
    md5(t.query)::uuid::varchar(100)                                AS query_md5,
    t.queryid::text                                                 AS queryid,
    left(regexp_replace(t.query, '\s+', ' ', 'g'), 10000)           AS query,
    left(m.query_mask, 10000)                                       AS query_mask
FROM top t
    CROSS JOIN LATERAL (
        SELECT regexp_replace(
                   regexp_replace(
                       regexp_replace(
                           regexp_replace(t.query, '\s+', ' ', 'g'),
                           '\$[0-9]+', '$0', 'g'),
                       '\(\s*\$0(\s*,\s*\$0)+\s*\)', '($0,$0)', 'g'),
                   '(\([$0, ]+\))(\s*,\s*\([$0, ]+\))+', '\1,...', 'g') AS query_mask
    ) m;
