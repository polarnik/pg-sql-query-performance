# Metrics catalog

Source of truth for what Telegraf collects. Every measurement has one SQL file in `sql/`, tested on
PostgreSQL 17 as a user that only has `pg_monitor` (see `config/postgresql/monitoring_user.sql`).

- Global tags on every metric: `db_instance` (`PG_INSTANCE`), `env` (`PG_ENV`), `host`; routing tags
  `db_and_stand` / `retention_policy` are consumed by the output and not stored.
- **Scope `cluster`** = collected once per instance through the maintenance DB (`postgres`, where the
  `pg_stat_statements` extension is created). **Scope `database`** = one connection per app database.
- Counters are cumulative since `stats_reset` / `stats_since`: tables use `spread()` (or `last()-first()`)
  over `$timeFilter`, time series use `non_negative_derivative(..., 1s)`.
- Text is never a tag: `query_short` / `query_mask_short` (≤120 chars) are fields; full text only in `pg_stmt_text`.
- Test all SQL: `for f in sql/*.sql; do case $f in *database_*) db=demo;; *) db=postgres;; esac; docker exec -i sql_monitor_postgres psql -X -v ON_ERROR_STOP=1 -U telegraf_monitoring_user -d $db -f - < $f >/dev/null || echo FAIL $f; done`

## Measurements

| measurement | SQL | scope | interval | tags | key fields | series / instance |
|---|---|---|---|---|---|---|
| `pg_settings_limits` | `sql/cluster_settings_limits.sql` | cluster | 5m | — | max_connections, superuser_reserved, reserved, effective_limit, client_backends, shared_buffers_bytes, work_mem_bytes, statement_timeout_ms, idle_in_transaction_session_timeout_ms, idle_session_timeout_ms, pg_stat_statements_max, track_activity_query_size_bytes, postmaster_start_epoch, server_version_num | 1 |
| `pg_db_limits` | `sql/cluster_db_limits.sql` | cluster | 30s | datname | datconnlimit, effective_conn_limit, numbackends, usage_pct | ≤10 |
| `pg_role_limits` | `sql/cluster_role_limits.sql` | cluster | 30s | rolname | rolconnlimit, effective_conn_limit, current, usage_pct | ≤50 |
| `pg_activity_grouped` | `sql/cluster_activity_grouped.sql` | cluster | 15s | datname, usename, application_name, state, wait_event_type | cnt, max_xact_age_s, max_state_age_s, max_backend_age_s | ≤300 |
| `pg_locks_blocked` | `sql/cluster_locks_blocked.sql` | cluster | 15s | datname | blocked, blocking, max_wait_s | ≤10 |
| `pg_db_stat` | `sql/cluster_db_stat.sql` | cluster | 60s | datname | xact_commit, xact_rollback, blks_read, blks_hit, tup_*, temp_files, temp_bytes, deadlocks, conflicts, blk_read_time, blk_write_time, session_time, active_time, idle_in_transaction_time, sessions*, stats_reset_epoch | ≤10 |
| `pg_stmt` | `sql/cluster_stmt.sql` | cluster | 5m | usename, datname, queryid, toplevel, query_md5, query_mask_md5 | calls, total_exec_time, plans, total_plan_time, rows, shared_blks_*, local_blks_read, temp_blks_*, shared_blk_*_time, temp_blk_*_time, wal_bytes, stats_since_epoch, query_short | ≤400 (grows with churn) |
| `pg_stmt_mask` | `sql/cluster_stmt_mask.sql` | cluster | 5m | usename, datname, query_mask_md5 | variants, calls, total_exec_time, rows, shared_blks_*, temp_blks_*, shared_blk_*_time, query_mask_short | ≤400 |
| `pg_stmt_text` | `sql/cluster_stmt_text.sql` | cluster | 30m | query_md5, query_mask_md5 | queryid, query (≤10000), query_mask (≤10000) | ≤400 |
| `pg_stmt_info` | `sql/cluster_stmt_info.sql` | cluster | 5m | — | dealloc, stats_reset_epoch, entries, max_entries | 1 |
| `pg_table_stat` | `sql/database_table_stat.sql` | database | 5m | datname, schemaname, relname | seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, n_tup_*, n_live_tup, n_dead_tup, dead_tup_pct, n_mod_since_analyze, n_ins_since_vacuum, *vacuum_count, *analyze_count, last_seq_scan_epoch, last_idx_scan_epoch, last_any_vacuum_epoch, last_any_analyze_epoch, total_bytes, table_bytes, indexes_bytes | ≤300 per DB |
| `pg_index_stat` | `sql/database_index_stat.sql` | database | 5m | datname, schemaname, relname, indexrelname | is_unique, is_primary, is_valid, idx_scan, idx_tup_read, idx_tup_fetch, last_idx_scan_epoch, index_bytes | ≤500 per DB |

Classic boards (`pgActivity` / `pgquery` / `pgstat`): `pg_stat_statements` (`sql/cluster_stat_statements.sql`, 60s),
`pg_stat_activity_count`, `pg_stat_activity_idle`, `pg_stat_activity_idle_in_transaction`, `pg_stat_activity_waiting`
(`sql/cluster_stat_activity_*.sql`, 5s) in `config/telegraf/telegraf.d/cluster_classic_boards.conf`; all instances,
Influx DBs `INFLUX_DB_STATEMENTS` / `INFLUX_DB_ACTIVITY`; docker-compose only (not shipped by `charts/pg-telegraf`).
No input uses inline `sqlquery`: every query is a `script = "/etc/telegraf/sql/<file>.sql"`.

## Cardinality budget
- Per instance with one app DB: ≈ 1 + 10 + 50 + 300 + 10 + 10 + 3×400 + 1 + 300 + 500 ≈ **2.4k** series.
- 4 instances ≈ 10k; with top-N churn over the retention window keep **`SHOW SERIES CARDINALITY` < 20k** per Influx DB.
- Levers if the budget is exceeded: lower top-N (200 → 100), shorter retention for `pg_stmt*`, drop `usename` from `pg_stmt_mask`.

## Mask rules (`pg_stmt`, `pg_stmt_mask`, `pg_stmt_text`)
1. `\s+` → one space.
2. `$1..$N` → `$0`.
3. IN-lists `($0, $0, ...)` → `($0,$0)`.
4. Repeated tuples `(...), (...), ...` (multi-row `VALUES`) → `(...),...`.
- md5 is computed on the full mask / query, truncation happens afterwards.
- Verified: `IN (1,2,3)`, `IN (1..6)`, `IN (7,8)` → one mask with `variants = 3`.
- `= ANY($1)` is already a single parameter and needs no rule.

## Prerequisites on a target instance (RDS)
- `shared_preload_libraries` contains `pg_stat_statements` (parameter group), `CREATE EXTENSION pg_stat_statements` in the maintenance DB — done by the DBA.
- `track_io_timing = on` for `*_blk_*_time` fields (otherwise they stay 0).
- `GRANT pg_monitor TO <monitoring user>`; `CONNECT` on each app DB; `sslmode=require` in `PG_DSN`.
