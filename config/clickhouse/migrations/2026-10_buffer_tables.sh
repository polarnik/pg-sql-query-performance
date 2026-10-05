#!/bin/bash
# One-off migration (history, D24): Buffer tables in front of the pg_monitoring MergeTree tables of a volume created
# before 01_schema.sql had them. A new volume does not need it: 01_schema.sql creates <T>_data + Buffer <T> directly
# (on such a volume the script is a no-op). Run by hand as the admin user, idempotent:
#   docker exec -i sql_monitor_clickhouse bash -c 'CLICKHOUSE_USER="$CH_ADMIN_USER" CLICKHOUSE_PASSWORD="$CH_ADMIN_PASSWORD" bash -s' \
#     < config/clickhouse/migrations/2026-10_buffer_tables.sh
# The Buffer arguments must stay equal to the ones in init/01_schema.sql.
#
# Why: Telegraf 1.32 outputs.sql sends one INSERT per metric (~3000 rows/min) with a random column order (Go map),
# so neither batching nor async inserts can group them: every row became its own part -> thousands of parts per
# minute, merges at 300%+ CPU on every Telegraf flush. A Buffer table keeps the rows in memory and writes one part
# per table every max_time seconds (or earlier at max_rows / max_bytes), whatever the column order.
#
#   pg_monitoring.<T>       Buffer   - Telegraf inserts here, Grafana reads here (buffer + <T>_data, transparent)
#   pg_monitoring.<T>_data  MergeTree / ReplacingMergeTree of the old 01_schema.sql (renamed) - storage, TTL, ALTERs
#
# Rows still in the buffer are flushed on a normal server stop and lost on a crash / kill -9 (<= max_time of data).
# Schema change of <T>_data (ADD COLUMN, ...): DROP TABLE <T> (the buffer is flushed), ALTER <T>_data, re-run this.
set -euo pipefail

DB=pg_monitoring
TABLES="pg_activity_grouped pg_locks_blocked pg_db_limits pg_role_limits pg_db_stat pg_settings_limits pg_stmt_info
pg_stmt pg_stmt_mask pg_stmt_totals pg_stmt_text pg_table_stat pg_index_stat"
# Buffer(database, table, num_layers, min_time, max_time, min_rows, max_rows, min_bytes, max_bytes)
BUFFER_ARGS="1, 10, 60, 100000, 1000000, 10000000, 100000000"

ch() {
    clickhouse client --host 127.0.0.1 \
        --user "${CLICKHOUSE_USER:-default}" --password "${CLICKHOUSE_PASSWORD:-}" "$@"
}

for t in $TABLES; do
    engine=$(ch -q "SELECT engine FROM system.tables WHERE database = '$DB' AND name = '$t'")
    if [ -n "$engine" ] && [ "$engine" != "Buffer" ]; then
        if [ "$(ch -q "EXISTS TABLE $DB.${t}_data")" = "1" ]; then
            echo "2026-10_buffer_tables.sh: both $DB.$t ($engine) and $DB.${t}_data exist, fix manually" >&2
            exit 1
        fi
        ch -q "RENAME TABLE $DB.$t TO $DB.${t}_data"
    fi
    ch -q "CREATE TABLE IF NOT EXISTS $DB.$t AS $DB.${t}_data ENGINE = Buffer($DB, ${t}_data, $BUFFER_ARGS)"
done

echo "2026-10_buffer_tables.sh: Buffer tables $DB.<table> -> $DB.<table>_data are up to date"
