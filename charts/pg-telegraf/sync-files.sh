#!/bin/sh
# Copy the tested docker-compose config into the chart (Helm can only read files inside the chart).
# Usage: charts/pg-telegraf/sync-files.sh [--check]   (--check: fail if files/ is out of date)
set -e
cd "$(dirname "$0")"
ROOT=../..
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/telegraf.d" "$TMP/sql" "$TMP/dashboards" "$TMP/influxdb"
cp "$ROOT/config/telegraf/telegraf.conf" "$TMP/telegraf.conf"
cp "$ROOT"/config/telegraf/telegraf.d/*.conf "$TMP/telegraf.d/"
cp "$ROOT"/sql/*.sql "$TMP/sql/"
# classic boards (pgActivity/pgquery/pgstat) and their Influx DBs exist only in docker-compose
rm -f "$TMP/telegraf.d/cluster_classic_boards.conf" "$TMP"/sql/cluster_stat_*.sql
cp "$ROOT"/config/grafana/provisioning/dashboards/json/pg-*.json "$TMP/dashboards/"
# RP "200d" + downsampling CQs for pg_monitoring (D16), applied by templates/influxdb-init-job.yaml
cp "$ROOT/config/influxdb/pg_monitoring_downsample.sh" "$TMP/influxdb/"

if [ "$1" = "--check" ]; then
    diff -r "$TMP" files && echo "files/ is up to date"
    exit $?
fi
rm -rf files
cp -R "$TMP" files
echo "synced into $(pwd)/files"
