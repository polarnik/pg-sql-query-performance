-- measurement: pg_stmt_mask | scope: cluster (DB with the pg_stat_statements extension) | interval: 5m
-- tags: usename, datname, query_mask_md5
-- fields: summed counters, variants (number of queryids behind the mask), query_mask_short (<=120 chars)
-- The mask is computed over ALL entries (so sums are complete), then top 200 masks by
-- cumulative total_exec_time UNION top 200 by calls are returned.
WITH masked AS (
    SELECT
        coalesce(r.rolname, s.userid::text)                         AS usename,
        coalesce(d.datname, s.dbid::text)                           AS datname,
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(s.query, '\s+', ' ', 'g'),
                    '\$[0-9]+', '$0', 'g'),
                '\(\s*\$0(\s*,\s*\$0)+\s*\)', '($0,$0)', 'g'),
            '(\([$0, ]+\))(\s*,\s*\([$0, ]+\))+', '\1,...', 'g')     AS query_mask,
        s.calls, s.total_exec_time, s.rows,
        s.shared_blks_hit, s.shared_blks_read, s.shared_blks_dirtied, s.shared_blks_written,
        s.temp_blks_read, s.temp_blks_written,
        s.shared_blk_read_time, s.shared_blk_write_time
    FROM pg_stat_statements s
        LEFT JOIN pg_roles r ON r.oid = s.userid
        LEFT JOIN pg_database d ON d.oid = s.dbid
    WHERE coalesce(r.rolname, '') NOT IN ('rdsadmin', 'rdsrepladmin')
), grouped AS (
    SELECT
        usename,
        datname,
        md5(query_mask)::uuid::varchar(100)                         AS query_mask_md5,
        left(query_mask, 120)                                       AS query_mask_short,
        count(*)                                                    AS variants,
        sum(calls)::bigint                                          AS calls,
        sum(total_exec_time)::float8                                AS total_exec_time,
        sum(rows)::bigint                                           AS rows,
        sum(shared_blks_hit)::bigint                                AS shared_blks_hit,
        sum(shared_blks_read)::bigint                               AS shared_blks_read,
        sum(shared_blks_dirtied)::bigint                            AS shared_blks_dirtied,
        sum(shared_blks_written)::bigint                            AS shared_blks_written,
        sum(temp_blks_read)::bigint                                 AS temp_blks_read,
        sum(temp_blks_written)::bigint                              AS temp_blks_written,
        sum(shared_blk_read_time)::float8                           AS shared_blk_read_time,
        sum(shared_blk_write_time)::float8                          AS shared_blk_write_time
    FROM masked
    GROUP BY usename, datname, query_mask
), ranked AS (
    SELECT g.*,
           row_number() OVER (ORDER BY total_exec_time DESC) AS rn_time,
           row_number() OVER (ORDER BY calls DESC)           AS rn_calls
    FROM grouped g
)
SELECT usename, datname, query_mask_md5, query_mask_short, variants,
       calls, total_exec_time, rows,
       shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written,
       temp_blks_read, temp_blks_written, shared_blk_read_time, shared_blk_write_time
FROM ranked
WHERE rn_time <= 200 OR rn_calls <= 200;
