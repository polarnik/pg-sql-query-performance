-- ClickHouse schema for the Telegraf `outputs.sql` (driver = "clickhouse") dual write.
-- Runs once on an empty data volume from /docker-entrypoint-initdb.d as the admin user; safe to re-run (IF NOT EXISTS).
--
-- One wide table per measurement. Telegraf does not create tables (writer has no DDL). Two tables per measurement <T>:
--   pg_monitoring.<T>_data  MergeTree (ReplacingMergeTree for pg_stmt_text) - storage: partitions, ORDER BY, TTL, ALTERs
--   pg_monitoring.<T>       Buffer -> <T>_data - Telegraf inserts here, Grafana reads here (buffer + <T>_data, transparent)
-- Why the Buffer: Telegraf 1.32 outputs.sql sends one INSERT per metric (~3000 rows/min) with a random column order
-- (Go map), so neither its batching nor async inserts can group them: one part per row, constant merges, high CPU.
-- The Buffer keeps rows in memory and writes one part per table every 60 s (or earlier at 1e6 rows / 100 MB);
-- Buffer(database, table, num_layers, min_time, max_time, min_rows, max_rows, min_bytes, max_bytes).
-- Rows still in the buffer are flushed on a normal server stop and lost on a crash / kill -9 (<= 60 s of data).
-- Schema change: DROP TABLE <T> (flushes the buffer), ALTER TABLE <T>_data ..., re-create <T> with the statement below.
-- Volumes created before the Buffer tables: config/clickhouse/migrations/2026-10_buffer_tables.sh.
-- Columns (Telegraf outputs.sql inserts one column per tag / field, the timestamp goes to `time`):
--   - tags   -> LowCardinality(String): global db_instance, env; postgresql_extensible server (= outputaddress),
--               db (= datname column or 'postgres'); the tagvalue columns of the input.
--               Routing tags db_and_stand / retention_policy are NOT stored (tagexclude on the output).
--   - fields -> integer -> Int64, float8 -> Float64, text -> String (types follow sql/*.sql).
--   - no Nullable: every column has a DEFAULT, a field missing in a metric (e.g. NULL usage_pct) becomes 0 / ''.
-- ORDER BY starts with db_instance + the dashboard filter columns, then time.
-- Raw data TTL: 30 days (change later with ALTER TABLE <table>_data ... MODIFY TTL toDateTime(time) + INTERVAL N DAY).

CREATE DATABASE IF NOT EXISTS pg_monitoring;

-- pg_activity_grouped | sql/cluster_activity_grouped.sql | 15s
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_activity_grouped_data
(
    time              DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance       LowCardinality(String) DEFAULT '',
    env               LowCardinality(String) DEFAULT '',
    server            LowCardinality(String) DEFAULT '',
    db                LowCardinality(String) DEFAULT '',
    datname           LowCardinality(String) DEFAULT '',
    usename           LowCardinality(String) DEFAULT '',
    application_name  LowCardinality(String) DEFAULT '',
    state             LowCardinality(String) DEFAULT '',
    wait_event_type   LowCardinality(String) DEFAULT '',
    cnt               Int64   DEFAULT 0 CODEC(T64, ZSTD),
    max_xact_age_s    Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    max_state_age_s   Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    max_backend_age_s Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, usename, application_name, state, wait_event_type, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_activity_grouped AS pg_monitoring.pg_activity_grouped_data
ENGINE = Buffer(pg_monitoring, pg_activity_grouped_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_locks_blocked | sql/cluster_locks_blocked.sql | 15s
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_locks_blocked_data
(
    time        DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance LowCardinality(String) DEFAULT '',
    env         LowCardinality(String) DEFAULT '',
    server      LowCardinality(String) DEFAULT '',
    db          LowCardinality(String) DEFAULT '',
    datname     LowCardinality(String) DEFAULT '',
    blocked     Int64   DEFAULT 0 CODEC(T64, ZSTD),
    blocking    Int64   DEFAULT 0 CODEC(T64, ZSTD),
    max_wait_s  Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_locks_blocked AS pg_monitoring.pg_locks_blocked_data
ENGINE = Buffer(pg_monitoring, pg_locks_blocked_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_db_limits | sql/cluster_db_limits.sql | 15s
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_db_limits_data
(
    time                 DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance          LowCardinality(String) DEFAULT '',
    env                  LowCardinality(String) DEFAULT '',
    server               LowCardinality(String) DEFAULT '',
    db                   LowCardinality(String) DEFAULT '',
    datname              LowCardinality(String) DEFAULT '',
    datconnlimit         Int64   DEFAULT 0 CODEC(T64, ZSTD),
    effective_conn_limit Int64   DEFAULT 0 CODEC(T64, ZSTD),
    numbackends          Int64   DEFAULT 0 CODEC(T64, ZSTD),
    usage_pct            Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_db_limits AS pg_monitoring.pg_db_limits_data
ENGINE = Buffer(pg_monitoring, pg_db_limits_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_role_limits | sql/cluster_role_limits.sql | 15s
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_role_limits_data
(
    time                 DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance          LowCardinality(String) DEFAULT '',
    env                  LowCardinality(String) DEFAULT '',
    server               LowCardinality(String) DEFAULT '',
    db                   LowCardinality(String) DEFAULT '',
    rolname              LowCardinality(String) DEFAULT '',
    rolconnlimit         Int64   DEFAULT 0 CODEC(T64, ZSTD),
    effective_conn_limit Int64   DEFAULT 0 CODEC(T64, ZSTD),
    current              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    usage_pct            Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, rolname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_role_limits AS pg_monitoring.pg_role_limits_data
ENGINE = Buffer(pg_monitoring, pg_role_limits_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_db_stat | sql/cluster_db_stat.sql | 1m | cumulative counters since stats_reset
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_db_stat_data
(
    time                     DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance              LowCardinality(String) DEFAULT '',
    env                      LowCardinality(String) DEFAULT '',
    server                   LowCardinality(String) DEFAULT '',
    db                       LowCardinality(String) DEFAULT '',
    datname                  LowCardinality(String) DEFAULT '',
    numbackends              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    xact_commit              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    xact_rollback            Int64   DEFAULT 0 CODEC(T64, ZSTD),
    blks_read                Int64   DEFAULT 0 CODEC(T64, ZSTD),
    blks_hit                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    tup_returned             Int64   DEFAULT 0 CODEC(T64, ZSTD),
    tup_fetched              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    tup_inserted             Int64   DEFAULT 0 CODEC(T64, ZSTD),
    tup_updated              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    tup_deleted              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    conflicts                Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_files               Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_bytes               Int64   DEFAULT 0 CODEC(T64, ZSTD),
    deadlocks                Int64   DEFAULT 0 CODEC(T64, ZSTD),
    checksum_failures        Int64   DEFAULT 0 CODEC(T64, ZSTD),
    blk_read_time            Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    blk_write_time           Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    session_time             Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    active_time              Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    idle_in_transaction_time Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    sessions                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    sessions_abandoned       Int64   DEFAULT 0 CODEC(T64, ZSTD),
    sessions_fatal           Int64   DEFAULT 0 CODEC(T64, ZSTD),
    sessions_killed          Int64   DEFAULT 0 CODEC(T64, ZSTD),
    stats_reset_epoch        Int64   DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_db_stat AS pg_monitoring.pg_db_stat_data
ENGINE = Buffer(pg_monitoring, pg_db_stat_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_settings_limits | sql/cluster_settings_limits.sql | 10m | one row per instance
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_settings_limits_data
(
    time                                   DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance                            LowCardinality(String) DEFAULT '',
    env                                    LowCardinality(String) DEFAULT '',
    server                                 LowCardinality(String) DEFAULT '',
    db                                     LowCardinality(String) DEFAULT '',
    max_connections                        Int64 DEFAULT 0 CODEC(T64, ZSTD),
    superuser_reserved                     Int64 DEFAULT 0 CODEC(T64, ZSTD),
    reserved                               Int64 DEFAULT 0 CODEC(T64, ZSTD),
    effective_limit                        Int64 DEFAULT 0 CODEC(T64, ZSTD),
    client_backends                        Int64 DEFAULT 0 CODEC(T64, ZSTD),
    shared_buffers_bytes                   Int64 DEFAULT 0 CODEC(T64, ZSTD),
    work_mem_bytes                         Int64 DEFAULT 0 CODEC(T64, ZSTD),
    maintenance_work_mem_bytes             Int64 DEFAULT 0 CODEC(T64, ZSTD),
    statement_timeout_ms                   Int64 DEFAULT 0 CODEC(T64, ZSTD),
    idle_in_transaction_session_timeout_ms Int64 DEFAULT 0 CODEC(T64, ZSTD),
    idle_session_timeout_ms                Int64 DEFAULT 0 CODEC(T64, ZSTD),
    pg_stat_statements_max                 Int64 DEFAULT 0 CODEC(T64, ZSTD),
    track_activity_query_size_bytes        Int64 DEFAULT 0 CODEC(T64, ZSTD),
    postmaster_start_epoch                 Int64 DEFAULT 0 CODEC(T64, ZSTD),
    server_version_num                     Int64 DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_settings_limits AS pg_monitoring.pg_settings_limits_data
ENGINE = Buffer(pg_monitoring, pg_settings_limits_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_stmt_info | sql/cluster_stmt_info.sql | 10m | one row per instance
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_info_data
(
    time              DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance       LowCardinality(String) DEFAULT '',
    env               LowCardinality(String) DEFAULT '',
    server            LowCardinality(String) DEFAULT '',
    db                LowCardinality(String) DEFAULT '',
    dealloc           Int64 DEFAULT 0 CODEC(T64, ZSTD),
    stats_reset_epoch Int64 DEFAULT 0 CODEC(T64, ZSTD),
    entries           Int64 DEFAULT 0 CODEC(T64, ZSTD),
    max_entries       Int64 DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_info AS pg_monitoring.pg_stmt_info_data
ENGINE = Buffer(pg_monitoring, pg_stmt_info_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_stmt | sql/cluster_stmt.sql | 1m | top-N statements, cumulative counters
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_data
(
    time                  DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance           LowCardinality(String) DEFAULT '',
    env                   LowCardinality(String) DEFAULT '',
    server                LowCardinality(String) DEFAULT '',
    db                    LowCardinality(String) DEFAULT '',
    usename               LowCardinality(String) DEFAULT '',
    datname               LowCardinality(String) DEFAULT '',
    queryid               String                 DEFAULT '',
    toplevel              LowCardinality(String) DEFAULT '',
    query_md5             String                 DEFAULT '',
    query_mask_md5        String                 DEFAULT '',
    query_short           String  DEFAULT '' CODEC(ZSTD(3)),
    calls                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    total_exec_time       Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    plans                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    total_plan_time       Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    rows                  Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_hit       Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_read      Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_dirtied   Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_written   Int64   DEFAULT 0 CODEC(T64, ZSTD),
    local_blks_read       Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_blks_read        Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_blks_written     Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blk_read_time  Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    shared_blk_write_time Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    temp_blk_read_time    Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    temp_blk_write_time   Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    wal_bytes             Int64   DEFAULT 0 CODEC(T64, ZSTD),
    stats_since_epoch     Int64   DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, usename, query_mask_md5, query_md5, queryid, toplevel, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt AS pg_monitoring.pg_stmt_data
ENGINE = Buffer(pg_monitoring, pg_stmt_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_stmt_mask | sql/cluster_stmt_mask.sql | 1m | top-N query masks, cumulative counters
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_mask_data
(
    time                  DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance           LowCardinality(String) DEFAULT '',
    env                   LowCardinality(String) DEFAULT '',
    server                LowCardinality(String) DEFAULT '',
    db                    LowCardinality(String) DEFAULT '',
    usename               LowCardinality(String) DEFAULT '',
    datname               LowCardinality(String) DEFAULT '',
    query_mask_md5        String                 DEFAULT '',
    query_mask_short      String  DEFAULT '' CODEC(ZSTD(3)),
    variants              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    calls                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    total_exec_time       Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    rows                  Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_hit       Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_read      Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_dirtied   Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_written   Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_blks_read        Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_blks_written     Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blk_read_time  Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    shared_blk_write_time Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, usename, query_mask_md5, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_mask AS pg_monitoring.pg_stmt_mask_data
ENGINE = Buffer(pg_monitoring, pg_stmt_mask_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_stmt_totals | sql/cluster_stmt_totals.sql | 1m | all pg_stat_statements entries by usename + datname
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_totals_data
(
    time                 DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance          LowCardinality(String) DEFAULT '',
    env                  LowCardinality(String) DEFAULT '',
    server               LowCardinality(String) DEFAULT '',
    db                   LowCardinality(String) DEFAULT '',
    usename              LowCardinality(String) DEFAULT '',
    datname              LowCardinality(String) DEFAULT '',
    statements           Int64   DEFAULT 0 CODEC(T64, ZSTD),
    calls                Int64   DEFAULT 0 CODEC(T64, ZSTD),
    total_exec_time      Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    rows                 Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_hit      Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blks_read     Int64   DEFAULT 0 CODEC(T64, ZSTD),
    temp_blks_written    Int64   DEFAULT 0 CODEC(T64, ZSTD),
    shared_blk_read_time Float64 DEFAULT 0 CODEC(Gorilla, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, usename, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_totals AS pg_monitoring.pg_stmt_totals_data
ENGINE = Buffer(pg_monitoring, pg_stmt_totals_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_stmt_text | sql/cluster_stmt_text.sql | 10m | md5 -> full text lookup, only the latest row per key is kept.
-- No partitioning: ReplacingMergeTree deduplicates within a partition only; use FINAL or argMax(query, time) in reads.
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_text_data
(
    time           DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance    LowCardinality(String) DEFAULT '',
    env            LowCardinality(String) DEFAULT '',
    server         LowCardinality(String) DEFAULT '',
    db             LowCardinality(String) DEFAULT '',
    query_md5      String                 DEFAULT '',
    query_mask_md5 String                 DEFAULT '',
    queryid        String                 DEFAULT '',
    query          String DEFAULT '' CODEC(ZSTD(3)),
    query_mask     String DEFAULT '' CODEC(ZSTD(3))
)
ENGINE = ReplacingMergeTree(time)
ORDER BY (env, db_instance, query_md5, queryid)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_stmt_text AS pg_monitoring.pg_stmt_text_data
ENGINE = Buffer(pg_monitoring, pg_stmt_text_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_table_stat | sql/database_table_stat.sql | 10m | top-N tables of the application DB
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_table_stat_data
(
    time                   DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance            LowCardinality(String) DEFAULT '',
    env                    LowCardinality(String) DEFAULT '',
    server                 LowCardinality(String) DEFAULT '',
    db                     LowCardinality(String) DEFAULT '',
    datname                LowCardinality(String) DEFAULT '',
    schemaname             LowCardinality(String) DEFAULT '',
    relname                LowCardinality(String) DEFAULT '',
    seq_scan               Int64   DEFAULT 0 CODEC(T64, ZSTD),
    seq_tup_read           Int64   DEFAULT 0 CODEC(T64, ZSTD),
    idx_scan               Int64   DEFAULT 0 CODEC(T64, ZSTD),
    idx_tup_fetch          Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_tup_ins              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_tup_upd              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_tup_del              Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_tup_hot_upd          Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_live_tup             Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_dead_tup             Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_mod_since_analyze    Int64   DEFAULT 0 CODEC(T64, ZSTD),
    n_ins_since_vacuum     Int64   DEFAULT 0 CODEC(T64, ZSTD),
    dead_tup_pct           Float64 DEFAULT 0 CODEC(Gorilla, ZSTD),
    vacuum_count           Int64   DEFAULT 0 CODEC(T64, ZSTD),
    autovacuum_count       Int64   DEFAULT 0 CODEC(T64, ZSTD),
    analyze_count          Int64   DEFAULT 0 CODEC(T64, ZSTD),
    autoanalyze_count      Int64   DEFAULT 0 CODEC(T64, ZSTD),
    last_seq_scan_epoch    Int64   DEFAULT 0 CODEC(T64, ZSTD),
    last_idx_scan_epoch    Int64   DEFAULT 0 CODEC(T64, ZSTD),
    last_any_vacuum_epoch  Int64   DEFAULT 0 CODEC(T64, ZSTD),
    last_any_analyze_epoch Int64   DEFAULT 0 CODEC(T64, ZSTD),
    total_bytes            Int64   DEFAULT 0 CODEC(T64, ZSTD),
    table_bytes            Int64   DEFAULT 0 CODEC(T64, ZSTD),
    indexes_bytes          Int64   DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, schemaname, relname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_table_stat AS pg_monitoring.pg_table_stat_data
ENGINE = Buffer(pg_monitoring, pg_table_stat_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);

-- pg_index_stat | sql/database_index_stat.sql | 10m | top-N indexes of the application DB
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_index_stat_data
(
    time                DateTime64(3)          CODEC(DoubleDelta, ZSTD),
    db_instance         LowCardinality(String) DEFAULT '',
    env                 LowCardinality(String) DEFAULT '',
    server              LowCardinality(String) DEFAULT '',
    db                  LowCardinality(String) DEFAULT '',
    datname             LowCardinality(String) DEFAULT '',
    schemaname          LowCardinality(String) DEFAULT '',
    relname             LowCardinality(String) DEFAULT '',
    indexrelname        LowCardinality(String) DEFAULT '',
    is_unique           Int64 DEFAULT 0 CODEC(T64, ZSTD),
    is_primary          Int64 DEFAULT 0 CODEC(T64, ZSTD),
    is_valid            Int64 DEFAULT 0 CODEC(T64, ZSTD),
    idx_scan            Int64 DEFAULT 0 CODEC(T64, ZSTD),
    idx_tup_read        Int64 DEFAULT 0 CODEC(T64, ZSTD),
    idx_tup_fetch       Int64 DEFAULT 0 CODEC(T64, ZSTD),
    last_idx_scan_epoch Int64 DEFAULT 0 CODEC(T64, ZSTD),
    index_bytes         Int64 DEFAULT 0 CODEC(T64, ZSTD)
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(time)
ORDER BY (db_instance, datname, schemaname, relname, indexrelname, time)
TTL toDateTime(time) + INTERVAL 30 DAY;
CREATE TABLE IF NOT EXISTS pg_monitoring.pg_index_stat AS pg_monitoring.pg_index_stat_data
ENGINE = Buffer(pg_monitoring, pg_index_stat_data, 1, 10, 60, 100000, 1000000, 10000000, 100000000);
