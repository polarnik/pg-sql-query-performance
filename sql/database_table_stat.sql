-- measurement: pg_table_stat | scope: per app database (connect to each DB) | interval: 5m
-- tags: datname, schemaname, relname
-- Top 300 tables by total size (cardinality budget). *_epoch = 0 means "never".
SELECT
    current_database()                                              AS datname,
    t.schemaname,
    t.relname,
    t.seq_scan,
    t.seq_tup_read,
    coalesce(t.idx_scan, 0)                                         AS idx_scan,
    coalesce(t.idx_tup_fetch, 0)                                    AS idx_tup_fetch,
    t.n_tup_ins,
    t.n_tup_upd,
    t.n_tup_del,
    t.n_tup_hot_upd,
    t.n_live_tup,
    t.n_dead_tup,
    t.n_mod_since_analyze,
    t.n_ins_since_vacuum,
    round(100.0 * t.n_dead_tup / nullif(t.n_live_tup + t.n_dead_tup, 0), 2)::float8 AS dead_tup_pct,
    t.vacuum_count,
    t.autovacuum_count,
    t.analyze_count,
    t.autoanalyze_count,
    coalesce(extract(epoch FROM t.last_seq_scan), 0)::bigint        AS last_seq_scan_epoch,
    coalesce(extract(epoch FROM t.last_idx_scan), 0)::bigint        AS last_idx_scan_epoch,
    coalesce(extract(epoch FROM greatest(t.last_vacuum, t.last_autovacuum)), 0)::bigint   AS last_any_vacuum_epoch,
    coalesce(extract(epoch FROM greatest(t.last_analyze, t.last_autoanalyze)), 0)::bigint AS last_any_analyze_epoch,
    pg_total_relation_size(t.relid)                                 AS total_bytes,
    pg_relation_size(t.relid)                                       AS table_bytes,
    pg_indexes_size(t.relid)                                        AS indexes_bytes
FROM pg_stat_user_tables t
ORDER BY pg_total_relation_size(t.relid) DESC
LIMIT 300;
