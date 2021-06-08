#!/bin/sh -x



influx -database 'telegraf_pg_demo' -type 'influxql'  <<-EOSQL
    SELECT
        sum(calls_diff) as calls_sum
    INTO
        telegraf_pg_demo."1d".pg_stat_statements_query_10m
    FROM (
        SELECT
            non_negative_difference(calls) AS calls_diff
        FROM
            telegraf_pg_demo."7d".pg_stat_statements
        WHERE
            time >= now() - 1d
        GROUP BY host, usename, datname, queryid, query_md5, "query"
    )
    WHERE
        calls_diff > 0 AND time >= now() - 1d
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(10m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo."1d".pg_stat_statements_query_60m
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_query_10m
    WHERE
        time >= now() - 1d
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(60m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        sum(calls_sum) AS calls_sum
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_1d
    FROM
        telegraf_pg_demo."1d".pg_stat_statements_query_60m
    WHERE
        time >= now() - 1d
    GROUP BY host, usename, datname, queryid, query_md5, "query", time(1d)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo."7d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 6h
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo."7d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 6h - 6h AND time <= now() - 6h
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo."7d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 12h - 6h AND time <= now() - 12h
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo."7d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 18h - 4h AND time <= now() - 18h
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        non_negative_difference(first(total_time)) AS "duration",
        non_negative_difference(first(calls)) AS calls,
        non_negative_difference(first(rows)) AS rows,
        non_negative_difference(first(shared_blks_hit)) AS shared_blks_hit,
        non_negative_difference(first(shared_blks_read)) AS shared_blks_read,
        non_negative_difference(first(shared_blks_dirtied)) AS shared_blks_dirtied,
        non_negative_difference(first(shared_blks_written)) AS shared_blks_written
    INTO
        telegraf_pg_demo."7d".pg_stat_statements_diff_1m
    FROM
        telegraf_pg_demo."7d".pg_stat_statements
    WHERE
        time >= now() - 22h - 4h AND time <= now() - 22h
    GROUP BY host, usename, datname, queryid, query_md5, time(1m)
EOSQL

influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        first(duration_sum) as duration_sum,
        first(duration_mean) as duration_mean,
        first(duration_stddev) as duration_stddev,
        first(calls_sum) as calls_sum,
        first(calls_mean) as calls_mean,
        first(calls_stddev) as calls_stddev,
        first(rows_sum) as rows_sum,
        first(rows_mean) as rows_mean,
        first(rows_stddev) as rows_stddev,
        first(shared_blks_hit_sum) as shared_blks_hit_sum,
        first(shared_blks_hit_mean) as shared_blks_hit_mean,
        first(shared_blks_hit_stddev) as shared_blks_hit_stddev,
        first(shared_blks_read_sum) as shared_blks_read_sum,
        first(shared_blks_read_mean) as shared_blks_read_mean,
        first(shared_blks_read_stddev) as shared_blks_read_stddev,
        first(shared_blks_dirtied_sum) as shared_blks_dirtied_sum,
        first(shared_blks_dirtied_mean) as shared_blks_dirtied_mean,
        first(shared_blks_dirtied_stddev) as shared_blks_dirtied_stddev,
        first(shared_blks_written_sum) as shared_blks_written_sum,
        first(shared_blks_written_mean) as shared_blks_written_mean,
        first(shared_blks_written_stddev) as shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10m
    FROM (
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
        FROM
            telegraf_pg_demo."7d".pg_stat_statements_diff_1m
        WHERE
            time >= now() - 30m
        GROUP BY host, usename, datname, queryid, query_md5
    )
    WHERE calls_sum > 0 and time >= now() - 30m
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
EOSQL



influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        first(duration_sum) as duration_sum,
        first(duration_mean) as duration_mean,
        first(duration_stddev) as duration_stddev,
        first(calls_sum) as calls_sum,
        first(calls_mean) as calls_mean,
        first(calls_stddev) as calls_stddev,
        first(rows_sum) as rows_sum,
        first(rows_mean) as rows_mean,
        first(rows_stddev) as rows_stddev,
        first(shared_blks_hit_sum) as shared_blks_hit_sum,
        first(shared_blks_hit_mean) as shared_blks_hit_mean,
        first(shared_blks_hit_stddev) as shared_blks_hit_stddev,
        first(shared_blks_read_sum) as shared_blks_read_sum,
        first(shared_blks_read_mean) as shared_blks_read_mean,
        first(shared_blks_read_stddev) as shared_blks_read_stddev,
        first(shared_blks_dirtied_sum) as shared_blks_dirtied_sum,
        first(shared_blks_dirtied_mean) as shared_blks_dirtied_mean,
        first(shared_blks_dirtied_stddev) as shared_blks_dirtied_stddev,
        first(shared_blks_written_sum) as shared_blks_written_sum,
        first(shared_blks_written_mean) as shared_blks_written_mean,
        first(shared_blks_written_stddev) as shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10m
    FROM (
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
        FROM
            telegraf_pg_demo."7d".pg_stat_statements_diff_1m
        WHERE
            time >= now() - 30m - 30m AND time <= now() - 30m
        GROUP BY host, usename, datname, queryid, query_md5
    )
    WHERE
        calls_sum > 0 AND time >= now() - 30m - 30m AND time <= now() - 30m
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
EOSQL


influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        first(duration_sum) as duration_sum,
        first(duration_mean) as duration_mean,
        first(duration_stddev) as duration_stddev,
        first(calls_sum) as calls_sum,
        first(calls_mean) as calls_mean,
        first(calls_stddev) as calls_stddev,
        first(rows_sum) as rows_sum,
        first(rows_mean) as rows_mean,
        first(rows_stddev) as rows_stddev,
        first(shared_blks_hit_sum) as shared_blks_hit_sum,
        first(shared_blks_hit_mean) as shared_blks_hit_mean,
        first(shared_blks_hit_stddev) as shared_blks_hit_stddev,
        first(shared_blks_read_sum) as shared_blks_read_sum,
        first(shared_blks_read_mean) as shared_blks_read_mean,
        first(shared_blks_read_stddev) as shared_blks_read_stddev,
        first(shared_blks_dirtied_sum) as shared_blks_dirtied_sum,
        first(shared_blks_dirtied_mean) as shared_blks_dirtied_mean,
        first(shared_blks_dirtied_stddev) as shared_blks_dirtied_stddev,
        first(shared_blks_written_sum) as shared_blks_written_sum,
        first(shared_blks_written_mean) as shared_blks_written_mean,
        first(shared_blks_written_stddev) as shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10m
    FROM (
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
        FROM
            telegraf_pg_demo."7d".pg_stat_statements_diff_1m
        WHERE
            time >= now() - 1h - 30m AND time <= now() - 1h
        GROUP BY host, usename, datname, queryid, query_md5
    )
    WHERE
        calls_sum > 0 AND time >= now() - 1h - 30m AND time <= now() - 1h
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
EOSQL



influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        first(duration_sum) as duration_sum,
        first(duration_mean) as duration_mean,
        first(duration_stddev) as duration_stddev,
        first(calls_sum) as calls_sum,
        first(calls_mean) as calls_mean,
        first(calls_stddev) as calls_stddev,
        first(rows_sum) as rows_sum,
        first(rows_mean) as rows_mean,
        first(rows_stddev) as rows_stddev,
        first(shared_blks_hit_sum) as shared_blks_hit_sum,
        first(shared_blks_hit_mean) as shared_blks_hit_mean,
        first(shared_blks_hit_stddev) as shared_blks_hit_stddev,
        first(shared_blks_read_sum) as shared_blks_read_sum,
        first(shared_blks_read_mean) as shared_blks_read_mean,
        first(shared_blks_read_stddev) as shared_blks_read_stddev,
        first(shared_blks_dirtied_sum) as shared_blks_dirtied_sum,
        first(shared_blks_dirtied_mean) as shared_blks_dirtied_mean,
        first(shared_blks_dirtied_stddev) as shared_blks_dirtied_stddev,
        first(shared_blks_written_sum) as shared_blks_written_sum,
        first(shared_blks_written_mean) as shared_blks_written_mean,
        first(shared_blks_written_stddev) as shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10m
    FROM (
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
        FROM
            telegraf_pg_demo."7d".pg_stat_statements_diff_1m
        WHERE
            time >= now() - 90m - 30m AND time <= now() - 90m
        GROUP BY host, usename, datname, queryid, query_md5
    )
    WHERE
        calls_sum > 0 AND time >= now() - 90m - 30m AND time <= now() - 90m
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
EOSQL



influx -database 'telegraf_pg_demo' -type 'influxql' <<-EOSQL
    SELECT
        first(duration_sum) as duration_sum,
        first(duration_mean) as duration_mean,
        first(duration_stddev) as duration_stddev,
        first(calls_sum) as calls_sum,
        first(calls_mean) as calls_mean,
        first(calls_stddev) as calls_stddev,
        first(rows_sum) as rows_sum,
        first(rows_mean) as rows_mean,
        first(rows_stddev) as rows_stddev,
        first(shared_blks_hit_sum) as shared_blks_hit_sum,
        first(shared_blks_hit_mean) as shared_blks_hit_mean,
        first(shared_blks_hit_stddev) as shared_blks_hit_stddev,
        first(shared_blks_read_sum) as shared_blks_read_sum,
        first(shared_blks_read_mean) as shared_blks_read_mean,
        first(shared_blks_read_stddev) as shared_blks_read_stddev,
        first(shared_blks_dirtied_sum) as shared_blks_dirtied_sum,
        first(shared_blks_dirtied_mean) as shared_blks_dirtied_mean,
        first(shared_blks_dirtied_stddev) as shared_blks_dirtied_stddev,
        first(shared_blks_written_sum) as shared_blks_written_sum,
        first(shared_blks_written_mean) as shared_blks_written_mean,
        first(shared_blks_written_stddev) as shared_blks_written_stddev
    INTO
        telegraf_pg_demo.autogen.pg_stat_statements_query_md5_10m
    FROM (
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
        FROM
            telegraf_pg_demo."7d".pg_stat_statements_diff_1m
        WHERE
            time >= now() - 2h - 30m AND time <= now() - 2h
        GROUP BY host, usename, datname, queryid, query_md5
    )
    WHERE
        calls_sum > 0 AND time >= now() - 2h - 30m AND time <= now() - 2h
    GROUP BY host, usename, datname, queryid, query_md5, time(10m)
EOSQL
