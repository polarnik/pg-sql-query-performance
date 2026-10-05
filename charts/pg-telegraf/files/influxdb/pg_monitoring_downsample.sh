#!/bin/sh
# pg_monitoring."7d" (raw, 5m..15s) -> pg_monitoring."200d" (1h rollups), same measurement and field names (D16).
# Idempotent: RP CREATE-or-ALTER, every CQ DROP + CREATE. Safe to re-run on a live InfluxDB:
#   docker exec sql_monitor_influxdb sh /opt/influxdb-init/pg_monitoring_downsample.sh
#   docker exec -e BACKFILL=1 sql_monitor_influxdb sh /opt/influxdb-init/pg_monitoring_downsample.sh
# INFLUX_ARGS: extra influx CLI flags (e.g. "-host influxdb -port 8086"); credentials: INFLUX_USERNAME / INFLUX_PASSWORD.
# INFLUX_DB_MONITORING: database (default pg_monitoring); it must already have the raw RP "7d".
# BACKFILL=1: also run each SELECT once over the raw history (BACKFILL_DAYS, default 7), one day per query.
# Aggregation: cumulative counters, settings, *_epoch, sizes, text -> last(); gauges -> max() (+ cnt_mean).
# Tags: explicit list without host/server/db (they differ per Telegraf container, not per monitored instance).
set -e

DB=${INFLUX_DB_MONITORING:-pg_monitoring}
SRC=7d
DST=200d
BACKFILL_DAYS=${BACKFILL_DAYS:-7}

q() {
    # q <statement>; -execute parses a single line only
    influx ${INFLUX_ARGS} -database "$DB" -execute "$(printf '%s' "$1" | tr '\n' ' ')"
}

if influx ${INFLUX_ARGS} -format csv -execute "SHOW RETENTION POLICIES ON \"$DB\"" | grep -q "^$DST,"; then
    q "ALTER RETENTION POLICY \"$DST\" ON \"$DB\" DURATION 200d REPLICATION 1 SHARD DURATION 7d"
else
    q "CREATE RETENTION POLICY \"$DST\" ON \"$DB\" DURATION 200d REPLICATION 1 SHARD DURATION 7d"
fi

agg() {
    # agg <fn> <field...> -> "fn(f) AS f, ..."
    fn=$1; shift
    out=""
    for f in "$@"; do out="$out${out:+, }$fn(\"$f\") AS \"$f\""; done
    printf '%s' "$out"
}

ds() {
    # ds <measurement> <tags> <select list>
    m=$1; tags=$2; fields=$3
    name="cq_${DST}_$m"
    select="SELECT $fields INTO \"$DB\".\"$DST\".\"$m\" FROM \"$DB\".\"$SRC\".\"$m\""
    group="GROUP BY time(1h), $tags"
    echo "$name"
    q "DROP CONTINUOUS QUERY $name ON $DB"
    q "CREATE CONTINUOUS QUERY $name ON $DB RESAMPLE EVERY 1h FOR 2h BEGIN $select $group END"
    if [ "$BACKFILL" = "1" ]; then
        # day chunks aligned to the hour, so no 1h bucket is split (a later partial write would overwrite max())
        hour=$(( $(date +%s) / 3600 * 3600 ))
        d=$BACKFILL_DAYS
        while [ "$d" -gt 0 ]; do
            q "$select WHERE time >= $((hour - d * 86400))s AND time < $((hour - (d - 1) * 86400))s $group" > /dev/null
            d=$((d - 1))
        done
        echo "  backfilled ${BACKFILL_DAYS}d"
    fi
}

I="db_instance, env"

ds pg_stmt "$I, datname, usename, queryid, query_md5, query_mask_md5, toplevel" "$(agg last \
    calls plans rows total_exec_time total_plan_time \
    shared_blks_hit shared_blks_read shared_blks_dirtied shared_blks_written local_blks_read \
    temp_blks_read temp_blks_written shared_blk_read_time shared_blk_write_time \
    temp_blk_read_time temp_blk_write_time wal_bytes stats_since_epoch query_short)"

ds pg_stmt_mask "$I, datname, usename, query_mask_md5" "$(agg last \
    calls rows total_exec_time shared_blks_hit shared_blks_read shared_blks_dirtied shared_blks_written \
    temp_blks_read temp_blks_written shared_blk_read_time shared_blk_write_time variants query_mask_short)"

ds pg_stmt_totals "$I, datname, usename" "$(agg last \
    statements calls rows total_exec_time shared_blks_hit shared_blks_read shared_blk_read_time temp_blks_written)"

ds pg_stmt_text "$I, query_md5, query_mask_md5" "$(agg last query query_mask queryid)"

ds pg_stmt_info "$I" "$(agg last dealloc entries max_entries stats_reset_epoch)"

ds pg_db_stat "$I, datname" "$(agg max numbackends), $(agg last \
    xact_commit xact_rollback blks_read blks_hit tup_returned tup_fetched tup_inserted tup_updated tup_deleted \
    conflicts temp_files temp_bytes deadlocks checksum_failures blk_read_time blk_write_time \
    session_time active_time idle_in_transaction_time sessions sessions_abandoned sessions_fatal sessions_killed \
    stats_reset_epoch)"

ds pg_table_stat "$I, datname, schemaname, relname" "$(agg max n_dead_tup dead_tup_pct), $(agg last \
    seq_scan seq_tup_read idx_scan idx_tup_fetch n_tup_ins n_tup_upd n_tup_del n_tup_hot_upd \
    n_live_tup n_mod_since_analyze n_ins_since_vacuum \
    vacuum_count autovacuum_count analyze_count autoanalyze_count \
    last_seq_scan_epoch last_idx_scan_epoch last_any_vacuum_epoch last_any_analyze_epoch \
    table_bytes indexes_bytes total_bytes)"

ds pg_index_stat "$I, datname, schemaname, relname, indexrelname" "$(agg last \
    idx_scan idx_tup_read idx_tup_fetch last_idx_scan_epoch index_bytes is_unique is_primary is_valid)"

ds pg_settings_limits "$I" "$(agg max client_backends), $(agg last \
    max_connections superuser_reserved reserved effective_limit \
    idle_in_transaction_session_timeout_ms idle_session_timeout_ms statement_timeout_ms \
    work_mem_bytes maintenance_work_mem_bytes shared_buffers_bytes track_activity_query_size_bytes \
    pg_stat_statements_max server_version_num postmaster_start_epoch)"

ds pg_db_limits "$I, datname" "$(agg max numbackends usage_pct), $(agg last datconnlimit effective_conn_limit)"

ds pg_role_limits "$I, rolname" "$(agg max current usage_pct), $(agg last rolconnlimit effective_conn_limit)"

ds pg_activity_grouped "$I, datname, usename, application_name, state, wait_event_type" \
    "$(agg max cnt max_xact_age_s max_state_age_s max_backend_age_s), mean(\"cnt\") AS \"cnt_mean\""

ds pg_locks_blocked "$I, datname" "$(agg max blocked blocking max_wait_s)"
