#!/bin/sh
# Databases, retention policies and continuous queries (D15).
# Idempotent: runs from /docker-entrypoint-initdb.d on an empty volume and can be re-run on a live InfluxDB:
#   docker exec sql_monitor_influxdb sh /docker-entrypoint-initdb.d/init.sh
# INFLUX_ARGS: extra influx CLI flags (e.g. "-host influxdb -port 8086 -username u -password p").
set -e

q() {
    # q <database> <statement>; -execute parses a single line only
    influx ${INFLUX_ARGS} -database "$1" -execute "$(printf '%s' "$2" | tr '\n' ' ')"
}

rp() {
    # rp <database> <name> <duration> <shard duration> [DEFAULT]: CREATE if missing, otherwise ALTER to the same spec
    if influx ${INFLUX_ARGS} -format csv -execute "SHOW RETENTION POLICIES ON \"$1\"" | grep -q "^$2,"; then
        q "$1" "ALTER RETENTION POLICY \"$2\" ON \"$1\" DURATION $3 REPLICATION 1 SHARD DURATION $4 $5"
    else
        q "$1" "CREATE RETENTION POLICY \"$2\" ON \"$1\" DURATION $3 REPLICATION 1 SHARD DURATION $4 $5"
    fi
}

cq() {
    # cq <database> <name> <RESAMPLE ... BEGIN ... END>: DROP (a no-op when missing) + CREATE
    echo "$2"
    q "$1" "DROP CONTINUOUS QUERY $2 ON $1"
    q "$1" "CREATE CONTINUOUS QUERY $2 ON $1 $3"
}

for db in telegraf_pg_demo telegraf_pg_activity_demo pg_monitoring jmeter gatling; do
    q _internal "CREATE DATABASE $db"
done

rp jmeter autogen 0s 1d DEFAULT
rp gatling autogen 0s 1d DEFAULT

# classic boards (pgquery / pgstat / pgActivity): archive keeps the same 200d horizon as pg_monitoring."200d"
rp telegraf_pg_demo archive 200d 1d
rp telegraf_pg_demo 1d 25h 1h DEFAULT

rp telegraf_pg_activity_demo archive 200d 1d
rp telegraf_pg_activity_demo 7d 7d 1h DEFAULT

rp pg_monitoring 7d 7d 1h DEFAULT

# pg_monitoring."200d": 1h rollups of every measurement (D16); mounted outside initdb.d so it does not run twice
PG_MONITORING_DOWNSAMPLE=${PG_MONITORING_DOWNSAMPLE:-/opt/influxdb-init/pg_monitoring_downsample.sh}
if [ -f "$PG_MONITORING_DOWNSAMPLE" ]; then
    INFLUX_ARGS="$INFLUX_ARGS" sh "$PG_MONITORING_DOWNSAMPLE"
fi

# Classic pg_stat_statements chain (inputs.d/cluster_classic_boards.conf, 60s):
#   1d.pg_stat_statements -> 1d.diff_1m -> 1d.diff_1m_active -> 1d.query_10m -> archive.query_1d / archive.filters
#                                                            \-> archive.diff_1m_archive
# host is stable (telegraf.conf hostname = PG_INSTANCE); toplevel is part of the pg_stat_statements key.
STMT_TAGS="host, db_instance, usename, datname, queryid, query_md5, query_mask_md5, toplevel"

cq telegraf_pg_demo cq_1d_pg_stat_statements_diff_1m "
RESAMPLE FOR 3m
BEGIN
    SELECT
        non_negative_difference(first(total_exec_time)) AS \"duration\",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo.\"1d\".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements
    GROUP BY $STMT_TAGS, time(1m, 0s)
END"

# InfluxQL has no HAVING: keep only the minutes with calls > 0
cq telegraf_pg_demo cq_1d_pg_stat_statements_diff_1m_active "
RESAMPLE FOR 4m
BEGIN
    SELECT
        first(\"duration\") AS \"duration\",
        first(calls) AS calls,
        first(rows) AS rows,
        first(shared_blks_hit) AS shared_blks_hit,
        first(shared_blks_read) AS shared_blks_read,
        first(shared_blks_dirtied) AS shared_blks_dirtied,
        first(shared_blks_written) AS shared_blks_written
    INTO
        telegraf_pg_demo.\"1d\".pg_stat_statements_diff_1m_active
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements_diff_1m
    WHERE
        calls > 0
    GROUP BY $STMT_TAGS, time(1m, 0s)
END"

cq telegraf_pg_demo cq_1d_pg_stat_statements_query_10m "
RESAMPLE FOR 20m
BEGIN
    SELECT
        sum(calls) AS calls_sum
    INTO
        telegraf_pg_demo.\"1d\".pg_stat_statements_query_10m
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements_diff_1m_active
    GROUP BY $STMT_TAGS, time(10m, 0s)
END"

# hourly, not every 10m: each run rescans the whole day for every series (issue #4, memory)
cq telegraf_pg_demo cq_archive_pg_stat_statements_query_1d "
RESAMPLE EVERY 1h FOR 1d
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo.\"archive\".pg_stat_statements_query_1d
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements_query_10m
    GROUP BY $STMT_TAGS, time(1d, 0s)
END"

cq telegraf_pg_demo cq_archive_pg_stat_statements_diff_1m_archive "
RESAMPLE FOR 5m
BEGIN
    SELECT
        first(\"duration\") AS \"duration\",
        first(calls) AS calls,
        first(rows) AS rows,
        first(shared_blks_hit) AS shared_blks_hit,
        first(shared_blks_read) AS shared_blks_read,
        first(shared_blks_dirtied) AS shared_blks_dirtied,
        first(shared_blks_written) AS shared_blks_written
    INTO
        telegraf_pg_demo.\"archive\".pg_stat_statements_diff_1m_archive
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements_diff_1m_active
    GROUP BY $STMT_TAGS, time(1m, 0s)
END"

cq telegraf_pg_demo cq_archive_pg_stat_statements_filters "
RESAMPLE EVERY 5m FOR 20m
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo.\"archive\".pg_stat_statements_filters
    FROM
        telegraf_pg_demo.\"1d\".pg_stat_statements_query_10m
    GROUP BY host, db_instance, usename, datname, time(10m, 0s)
END"
