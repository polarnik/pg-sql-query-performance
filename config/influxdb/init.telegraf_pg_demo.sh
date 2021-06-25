#!/bin/sh -x

DB=telegraf_pg_demo

influx <<-EOSQL
CREATE DATABASE $DB;
EOSQL

influx <<-EOSQL
CREATE RETENTION POLICY "archive" ON "$DB" DURATION 1000d REPLICATION 1 SHARD DURATION 1d;
EOSQL
influx <<-EOSQL
CREATE RETENTION POLICY "1d" ON "$DB" DURATION 25h REPLICATION 1 SHARD DURATION 1h DEFAULT;
EOSQL


echo "cq_1d_pg_stat_statements_diff_1m"
influx -database "$DB" -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m
    ON $DB ;
EOSQL
influx -database "$DB" -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m
    ON $DB
RESAMPLE FOR 2m
BEGIN
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        $DB."1d".pg_stat_statements_diff_1m
    FROM
        $DB."1d".pg_stat_statements
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1m, 0s)
END;
EOSQL

echo "cq_1d_pg_stat_statements_diff_1m_active"
influx -database "$DB" -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m_active
    ON $DB ;
EOSQL
influx -database "$DB" -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m_active
    ON $DB
RESAMPLE FOR 3m
BEGIN
    SELECT
        first("duration") as "duration",
        first(calls) as calls,
        first(rows) as rows,
        first(shared_blks_hit) as shared_blks_hit,
        first(shared_blks_read) as shared_blks_read,
        first(shared_blks_dirtied) as shared_blks_dirtied,
        first(shared_blks_written) as shared_blks_written
    INTO
        $DB."1d".pg_stat_statements_diff_1m_active
    FROM
        $DB."1d".pg_stat_statements_diff_1m
    WHERE
        calls > 0
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1m, 0s)
END;
EOSQL

echo "cq_1d_pg_stat_statements_query_10m"
influx -database "$DB" -type 'influxql'  <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_query_10m
    ON $DB ;
EOSQL
influx -database "$DB" -type 'influxql'  <<-EOSQL
CREATE     
    CONTINUOUS QUERY cq_1d_pg_stat_statements_query_10m
    ON $DB
RESAMPLE FOR 20m
BEGIN
    SELECT
        sum(calls) as calls_sum
    INTO
        $DB."1d".pg_stat_statements_query_10m
    FROM
        $DB."1d".pg_stat_statements_diff_1m_active
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(10m, 0s)
END;
EOSQL


echo "cq_archive_pg_stat_statements_query_1d"
influx -database "$DB" -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_query_1d
    ON $DB
EOSQL
influx -database "$DB" -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_query_1d
    ON $DB
RESAMPLE EVERY 10m FOR 1d
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        $DB."archive".pg_stat_statements_query_1d
    FROM
        $DB."1d".pg_stat_statements_query_10m
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1d, 0s)
END;
EOSQL



echo "cq_archive_pg_stat_statements_diff_1m_archive"
influx -database "$DB" -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_diff_1m_archive
    ON $DB ;
EOSQL
influx -database "$DB" -type 'influxql' <<-EOSQL

CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_diff_1m_archive
    ON $DB
RESAMPLE FOR 4m
BEGIN
    SELECT
        first("duration") as "duration",
        first(calls) as calls,
        first(rows) as rows,
        first(shared_blks_hit) as shared_blks_hit,
        first(shared_blks_read) as shared_blks_read,
        first(shared_blks_dirtied) as shared_blks_dirtied,
        first(shared_blks_written) as shared_blks_written
    INTO
        $DB."archive".pg_stat_statements_diff_1m_archive
    FROM
        $DB."1d".pg_stat_statements_diff_1m_active
    GROUP BY host, usename, datname, queryid, query_md5, time(1m, 0s)
END;
EOSQL

echo "cq_archive_pg_stat_statements_filters"
influx -database "$DB" -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_filters
    ON $DB ;
EOSQL
influx -database "$DB" -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_filters
    ON $DB
RESAMPLE EVERY 5m FOR 20m
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        $DB."archive".pg_stat_statements_filters
    FROM
        $DB."1d".pg_stat_statements_query_10m
    GROUP BY host, usename, datname, time(10m, 0s)
END;
EOSQL