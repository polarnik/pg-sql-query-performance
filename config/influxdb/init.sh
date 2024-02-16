#!/bin/sh -x

login="admin"
password="password_123"
echo "Create databases - Start"
echo "1)"
influx -type 'influxql' -execute "CREATE USER $login WITH PASSWORD '$password' WITH ALL PRIVILEGES;"
echo "2)"
influx -type 'influxql' -execute "CREATE DATABASE telegraf_pg_demo;"
echo "3)"
influx -type 'influxql' -execute "CREATE DATABASE telegraf_pg_activity_demo;"
echo "4)"
influx -type 'influxql' -execute "CREATE DATABASE jmeter;"
echo "5)"
influx -type 'influxql' -execute "CREATE DATABASE gatling;"
echo "Create databases - Complete"


influx <<-EOSQL
CREATE RETENTION POLICY "autogen" ON "jmeter" DURATION 0s REPLICATION 1 SHARD DURATION 1d DEFAULT;
CREATE RETENTION POLICY "autogen" ON "gatling" DURATION 0s REPLICATION 1 SHARD DURATION 1d DEFAULT;

CREATE RETENTION POLICY "archive" ON "telegraf_pg_demo" DURATION 1000d REPLICATION 1 SHARD DURATION 1d;
CREATE RETENTION POLICY "1d" ON "telegraf_pg_demo" DURATION 25h REPLICATION 1 SHARD DURATION 1h DEFAULT;

CREATE RETENTION POLICY "archive" ON "telegraf_pg_activity_demo" DURATION 1000d REPLICATION 1 SHARD DURATION 1d;
CREATE RETENTION POLICY "7d" ON "telegraf_pg_activity_demo" DURATION 7d REPLICATION 1 SHARD DURATION 1h DEFAULT;
EOSQL

echo "cq_1d_pg_stat_statements_diff_1m"
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m
    ON telegraf_pg_demo ;
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m
    ON telegraf_pg_demo
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
        telegraf_pg_demo."1d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."1d".pg_stat_statements
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1m, 0s)
END;
EOSQL

echo "cq_1d_pg_stat_statements_diff_1m_active"
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m_active
    ON telegraf_pg_demo ;
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_1d_pg_stat_statements_diff_1m_active
    ON telegraf_pg_demo
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
        telegraf_pg_demo."1d".pg_stat_statements_diff_1m_active
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_diff_1m
    WHERE
        calls > 0
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1m, 0s)
END;
EOSQL

echo "cq_1d_pg_stat_statements_query_10m"
influx -database 'telegraf_pg_demo' -type 'influxql'  <<-EOSQL
DROP
    CONTINUOUS QUERY cq_1d_pg_stat_statements_query_10m
    ON telegraf_pg_demo ;
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql'  <<-EOSQL
CREATE     
    CONTINUOUS QUERY cq_1d_pg_stat_statements_query_10m
    ON telegraf_pg_demo
RESAMPLE FOR 20m
BEGIN
    SELECT
        sum(calls) as calls_sum
    INTO
        telegraf_pg_demo."1d".pg_stat_statements_query_10m
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_diff_1m_active
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(10m, 0s)
END;
EOSQL


echo "cq_archive_pg_stat_statements_query_1d"
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_query_1d
    ON telegraf_pg_demo
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_query_1d
    ON telegraf_pg_demo
RESAMPLE EVERY 10m FOR 1d
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo."archive".pg_stat_statements_query_1d
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_query_10m
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1d, 0s)
END;
EOSQL



echo "cq_archive_pg_stat_statements_diff_1m_archive"
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_diff_1m_archive
    ON telegraf_pg_demo ;
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL

CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_diff_1m_archive
    ON telegraf_pg_demo
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
        telegraf_pg_demo."archive".pg_stat_statements_diff_1m_archive
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_diff_1m_active
    GROUP BY host, usename, datname, queryid, query_md5, time(1m, 0s)
END;
EOSQL

echo "cq_archive_pg_stat_statements_filters"
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
DROP
    CONTINUOUS QUERY cq_archive_pg_stat_statements_filters
    ON telegraf_pg_demo ;
EOSQL
influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
CREATE
    CONTINUOUS QUERY cq_archive_pg_stat_statements_filters
    ON telegraf_pg_demo
RESAMPLE EVERY 5m FOR 20m
BEGIN
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo."archive".pg_stat_statements_filters
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_query_10m
    GROUP BY host, usename, datname, time(10m, 0s)
END;
EOSQL

