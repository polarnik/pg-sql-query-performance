-- measurement: pg_stmt_totals | scope: cluster (DB with the pg_stat_statements extension) | interval: 5m
-- tags: usename, datname
-- fields: counters summed over ALL pg_stat_statements entries (no top-N cut), statements (number of entries)
-- Complete totals for the datname / datname+db_instance / datname+usename breakdowns on pg-statements.
-- Cardinality: users x databases per instance.
SELECT
    coalesce(r.rolname, s.userid::text)                             AS usename,
    coalesce(d.datname, s.dbid::text)                               AS datname,
    count(*)                                                        AS statements,
    sum(s.calls)::bigint                                            AS calls,
    sum(s.total_exec_time)::float8                                  AS total_exec_time,
    sum(s.rows)::bigint                                             AS rows,
    sum(s.shared_blks_hit)::bigint                                  AS shared_blks_hit,
    sum(s.shared_blks_read)::bigint                                 AS shared_blks_read,
    sum(s.temp_blks_written)::bigint                                AS temp_blks_written,
    sum(s.shared_blk_read_time)::float8                             AS shared_blk_read_time
FROM pg_stat_statements s
    LEFT JOIN pg_roles r ON r.oid = s.userid
    LEFT JOIN pg_database d ON d.oid = s.dbid
WHERE coalesce(r.rolname, '') NOT IN ('rdsadmin', 'rdsrepladmin')
GROUP BY 1, 2;
