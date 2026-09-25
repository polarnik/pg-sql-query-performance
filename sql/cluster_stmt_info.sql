-- measurement: pg_stmt_info | scope: cluster (DB with the pg_stat_statements extension) | interval: 5m
-- tags: db_instance (global)
-- dealloc grows when pg_stat_statements.max is too small (entries evicted) -> stats become incomplete.
SELECT
    dealloc,
    coalesce(extract(epoch FROM stats_reset), 0)::bigint            AS stats_reset_epoch,
    (SELECT count(*) FROM pg_stat_statements)                       AS entries,
    coalesce(current_setting('pg_stat_statements.max', true), '0')::int AS max_entries
FROM pg_stat_statements_info;
