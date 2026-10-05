# Metrics catalog

Source of truth for what Telegraf collects. Every measurement has one SQL file in `sql/`, tested on
PostgreSQL 17 as a user that only has `pg_monitor` (see `config/postgresql/monitoring_user.sql`).

- Global tags on every metric: `db_instance` (`PG_INSTANCE`), `env` (`PG_ENV`), `host`; routing tags
  `db_and_stand` / `retention_policy` are consumed by the output and not stored.
- Storage: InfluxDB `pg_monitoring` (`pg-*` boards) **and** ClickHouse `pg_monitoring.<measurement>` (`ch-*` boards),
  see [ClickHouse tables](#clickhouse-tables-pg_monitoring-d17d18).
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
| `pg_stmt_totals` | `sql/cluster_stmt_totals.sql` | cluster | 5m | usename, datname | statements (entries), calls, total_exec_time, rows, shared_blks_hit, shared_blks_read, temp_blks_written, shared_blk_read_time — summed over **all** entries (no top-N) | users × databases (demo: 15) |
| `pg_stmt_text` | `sql/cluster_stmt_text.sql` | cluster | 30m | query_md5, query_mask_md5 | queryid, query (≤10000), query_mask (≤10000) | ≤400 |
| `pg_stmt_info` | `sql/cluster_stmt_info.sql` | cluster | 5m | — | dealloc, stats_reset_epoch, entries, max_entries | 1 |
| `pg_table_stat` | `sql/database_table_stat.sql` | database | 5m | datname, schemaname, relname | seq_scan, seq_tup_read, idx_scan, idx_tup_fetch, n_tup_*, n_live_tup, n_dead_tup, dead_tup_pct, n_mod_since_analyze, n_ins_since_vacuum, *vacuum_count, *analyze_count, last_seq_scan_epoch, last_idx_scan_epoch, last_any_vacuum_epoch, last_any_analyze_epoch, total_bytes, table_bytes, indexes_bytes | ≤300 per DB |
| `pg_index_stat` | `sql/database_index_stat.sql` | database | 5m | datname, schemaname, relname, indexrelname | is_unique, is_primary, is_valid, idx_scan, idx_tup_read, idx_tup_fetch, last_idx_scan_epoch, index_bytes | ≤500 per DB |

Classic boards (`pgActivity` / `pgquery` / `pgstat`): `pg_stat_statements` (`sql/cluster_stat_statements.sql`, 60s),
`pg_stat_activity_count`, `pg_stat_activity_idle`, `pg_stat_activity_idle_in_transaction`, `pg_stat_activity_waiting`
(`sql/cluster_stat_activity_*.sql`, 5s) in `config/telegraf/telegraf.d/cluster_classic_boards.conf`; all instances,
Influx DBs `INFLUX_DB_STATEMENTS` / `INFLUX_DB_ACTIVITY`; docker-compose only (not shipped by `charts/pg-telegraf`).
No input uses inline `sqlquery`: every query is a `script = "/etc/telegraf/sql/<file>.sql"`.

`pg_stmt_totals` feeds the Breakdown row of `pg-statements` (by datname / datname+db_instance / datname+usename).
It is not a sum of `pg_stmt_mask`: top-N tables are a subset, their totals are always ≤ Breakdown totals.
Increase over the range = `sum(non_negative_difference(last(x)))` per series, then `sum` per breakdown (D14);
evicted entries (`pg_stmt_info.dealloc`) make the sum drop, such steps are ignored.

## Cardinality budget
- Per instance with one app DB: ≈ 1 + 10 + 50 + 300 + 10 + 10 + 3×400 + 20 + 1 + 300 + 500 ≈ **2.4k** series.
- 4 instances ≈ 10k; with top-N churn over the retention window keep **`SHOW SERIES CARDINALITY` < 20k** per Influx DB.
- Levers if the budget is exceeded: lower top-N (200 → 100), shorter retention for `pg_stmt*`, drop `usename` from `pg_stmt_mask`.

## Retention policies (`pg_monitoring`, D16)
| RP | resolution | duration | written by |
|---|---|---|---|
| `7d` (DEFAULT) | raw (15s … 30m, see interval) | 7d | Telegraf |
| `200d` | 1h | 200d, shard 7d | CQ `cq_200d_<measurement>` (`config/influxdb/pg_monitoring_downsample.sh`) |

- Same measurement and field names in both RPs; `200d` drops the tags `host`, `server`, `db`.
- Aggregation per 1h: cumulative counters, settings, `*_epoch`, sizes and text → `last()`, so increases are computed
  the same way as on raw data (`non_negative_difference(last())`). Gauges → `max()`: `pg_activity_grouped` (all fields,
  plus `cnt_mean` = `mean(cnt)`), `pg_locks_blocked`, `numbackends`, `usage_pct`, `current`, `client_backends`,
  `n_dead_tup`, `dead_tup_pct`.
- Apply / re-apply on a running InfluxDB (idempotent; `BACKFILL=1` also rolls up the raw 7d):
  `docker exec -e BACKFILL=1 sql_monitor_influxdb sh /opt/influxdb-init/pg_monitoring_downsample.sh`.
- `200d` ≈ ⅓ of the `7d` series (no `host` churn): ≈ 5.9k series on the demo stand.

## ClickHouse tables (`pg_monitoring`, D17–D18)
The same 13 measurements are also written by `[[outputs.sql]]` (`config/telegraf/telegraf.d/output_clickhouse.conf`)
into ClickHouse database `pg_monitoring`, one table per measurement, **table name = measurement name**.
Source of truth for columns, types and codecs: `config/clickhouse/init/01_schema.sql` (a column missing there fails the
whole insert of that table → add new SQL fields to the schema first).

- Common columns in every table: `time DateTime64(3)`, `db_instance`, `env`, `server`, `db` (`LowCardinality(String)`).
  Not stored: `db_and_stand`, `retention_policy`, `host` (`tagexclude` on the output).
- Tags (columns from the measurements table above) → `LowCardinality(String)`, except the md5 / id keys
  `query_md5`, `query_mask_md5`, `queryid` → `String`. Fields: integer → `Int64`, float → `Float64`, text → `String`.
- No `Nullable`: every column has `DEFAULT 0` / `''` (NULL `usage_pct`, empty `datname` → default).
- `PARTITION BY toYYYYMMDD(time)` (except `pg_stmt_text`), `TTL toDateTime(time) + INTERVAL 30 DAY`, no rollups.

| table | engine | ORDER BY (after `db_instance`) | notes |
|---|---|---|---|
| `pg_settings_limits` | MergeTree | `time` | one row per instance |
| `pg_stmt_info` | MergeTree | `time` | one row per instance; `stats_reset_epoch`, `dealloc` |
| `pg_db_limits` | MergeTree | `datname, time` | |
| `pg_role_limits` | MergeTree | `rolname, time` | |
| `pg_activity_grouped` | MergeTree | `datname, usename, application_name, state, wait_event_type, time` | gauges |
| `pg_locks_blocked` | MergeTree | `datname, time` | gauges |
| `pg_db_stat` | MergeTree | `datname, time` | cumulative counters |
| `pg_stmt` | MergeTree | `datname, usename, query_mask_md5, query_md5, queryid, toplevel, time` | `query_short` = `String` field |
| `pg_stmt_mask` | MergeTree | `datname, usename, query_mask_md5, time` | `query_mask_short` = `String` field |
| `pg_stmt_totals` | MergeTree | `datname, usename, time` | all entries, no top-N |
| `pg_stmt_text` | ReplacingMergeTree(time), not partitioned | `query_md5` | latest `query` / `query_mask` per md5; read with `argMax(…, time)` / `FINAL` |
| `pg_table_stat` | MergeTree | `datname, schemaname, relname, time` | |
| `pg_index_stat` | MergeTree | `datname, schemaname, relname, indexrelname, time` | |

- Counters stay cumulative: `ch-*` boards compute increases as the sum of positive steps per series (never negative,
  resets / dealloc handled, D20c) instead of InfluxQL `spread()` / `non_negative_difference()`.
- Check row counts per table and instance (as `reader`):
  `docker exec sql_monitor_clickhouse clickhouse-client --user reader --password reader -q "SELECT count(), uniq(db_instance) FROM pg_monitoring.pg_stmt_mask"`.
- Users: `writer` (Telegraf, `INSERT, SELECT`), `reader` (Grafana datasource `pg-monitoring-ch`, `SELECT`, readonly), `admin` (D19).

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
