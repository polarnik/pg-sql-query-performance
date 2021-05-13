#!/bin/sh -x

influx <<-EOSQL
CREATE DATABASE telegraf_pg_demo;
EOSQL

influx <<-EOSQL
CREATE RETENTION POLICY "7d" ON "telegraf_pg_demo" DURATION 7d REPLICATION 1 DEFAULT;
CREATE
    CONTINUOUS QUERY pg_stat_statements_query_text
    ON telegraf_pg_demo
BEGIN
    SELECT
        first("t") AS "t"
    INTO telegraf_pg_demo.autogen.pg_stat_statements_query_text_1d
    FROM (
        SELECT difference(first(calls)) AS t
        FROM telegraf_pg_demo."7d".pg_stat_statements
        WHERE time >= now() - 1d
        GROUP BY host, queryid, query_md5, "query", time(2h)
    )
    WHERE t != 0
    GROUP BY host, queryid, query_md5, "query", time(1d)
END;
EOSQL

influx <<-EOSQL
CREATE
    CONTINUOUS QUERY pg_stat_statements_diff_1m
    ON telegraf_pg_demo
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
        telegraf_pg_demo."7d".pg_stat_statements_diff
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 1m
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
END;
EOSQL

influx <<-EOSQL
CREATE
    CONTINUOUS QUERY pg_stat_statements_query_md5_10min
    ON telegraf_pg_demo
BEGIN
    SELECT
        sum("duration") AS duration_sum,
        mean("duration") AS duration_mean,
        stddev("duration") AS duration_stddev,
        sum(calls) AS calls_sum,
        mean(calls) AS calls_mean,
        stddev(calls) AS calls_stddev,
        sum(rows) AS rows_sum,
        mean(rows) AS rows_mean,
        stddev(rows) AS rows_stddev,
        sum(shared_blks_hit) AS shared_blks_hit_sum,
        mean(shared_blks_hit) AS shared_blks_hit_mean,
        stddev(shared_blks_hit) AS shared_blks_hit_stddev,
        sum(shared_blks_read) AS shared_blks_read_sum,
        mean(shared_blks_read) AS shared_blks_read_mean,
        stddev(shared_blks_read) AS shared_blks_read_stddev,
        sum(shared_blks_dirtied) AS shared_blks_dirtied_sum,
        mean(shared_blks_dirtied) AS shared_blks_dirtied_mean,
        stddev(shared_blks_dirtied) AS shared_blks_dirtied_stddev,
        sum(shared_blks_written) AS shared_blks_written_sum,
        mean(shared_blks_written) AS shared_blks_written_mean,
        stddev(shared_blks_written) AS shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10min
    FROM
        telegraf_pg_demo."7d".pg_stat_statements_diff
    WHERE
        time >= now() - 20m AND
        calls > 0
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
END;
EOSQL