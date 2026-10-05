#!/bin/bash
# Least-privilege ClickHouse users for the pg_monitoring database.
# Runs from /docker-entrypoint-initdb.d after 01_schema.sql, as the admin user ($CLICKHOUSE_USER, access management on).
# Idempotent: IF NOT EXISTS + ALTER, so a re-run (CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS=1 or manual) also applies new passwords.
#   writer - Telegraf outputs.sql: INSERT, SELECT on pg_monitoring.* (SELECT for table_exists_template), sync inserts
#   reader - Grafana: SELECT on pg_monitoring.* only, readonly=2 (may change query settings, no writes / DDL), limits
# Passwords come from env (.env.example defaults, override in a git-ignored .env.clickhouse).
set -euo pipefail

: "${CH_WRITER_USER:=writer}"
: "${CH_READER_USER:=reader}"
: "${CH_WRITER_PASSWORD:?CH_WRITER_PASSWORD is not set}"
: "${CH_READER_PASSWORD:?CH_READER_PASSWORD is not set}"

# Escape a value for a single-quoted ClickHouse string literal.
sql_quote() {
    local s=${1//\\/\\\\}
    printf "'%s'" "${s//\'/\\\'}"
}

writer_pw=$(sql_quote "$CH_WRITER_PASSWORD")
reader_pw=$(sql_quote "$CH_READER_PASSWORD")

clickhouse client --host 127.0.0.1 \
    --user "${CLICKHOUSE_USER:-default}" --password "${CLICKHOUSE_PASSWORD:-}" \
    --multiquery <<SQL
-- Telegraf outputs.sql sends one INSERT per metric (~3000 rows/min, random column order). Batching is done by the
-- Buffer tables of 01_schema.sql: plain synchronous inserts into memory, errors are returned to Telegraf.
-- (async_insert + wait_for_async_insert = 1 made one part per row: constant merges, Telegraf missed its flush interval.)
-- Successful writer queries are not logged to query_log (2 rows per inserted row otherwise), exceptions still are.
CREATE SETTINGS PROFILE IF NOT EXISTS writer_profile;
ALTER SETTINGS PROFILE writer_profile SETTINGS
    async_insert = 0,
    log_queries_min_type = 'EXCEPTION_BEFORE_START',
    max_execution_time = 60;

CREATE SETTINGS PROFILE IF NOT EXISTS reader_profile;
ALTER SETTINGS PROFILE reader_profile SETTINGS
    readonly = 2 CONST,
    max_execution_time = 30 MAX 60,
    max_memory_usage = 2000000000 MAX 2000000000,
    max_result_rows = 1000000 MAX 1000000,
    max_rows_to_read = 1000000000 MAX 1000000000;

CREATE USER IF NOT EXISTS ${CH_WRITER_USER};
ALTER USER ${CH_WRITER_USER} IDENTIFIED WITH sha256_password BY ${writer_pw}
    DEFAULT DATABASE pg_monitoring SETTINGS PROFILE 'writer_profile';
REVOKE ALL ON *.* FROM ${CH_WRITER_USER};
GRANT INSERT, SELECT ON pg_monitoring.* TO ${CH_WRITER_USER};

CREATE USER IF NOT EXISTS ${CH_READER_USER};
ALTER USER ${CH_READER_USER} IDENTIFIED WITH sha256_password BY ${reader_pw}
    DEFAULT DATABASE pg_monitoring SETTINGS PROFILE 'reader_profile';
REVOKE ALL ON *.* FROM ${CH_READER_USER};
GRANT SELECT ON pg_monitoring.* TO ${CH_READER_USER};
SQL

echo "02_users.sh: users ${CH_WRITER_USER}, ${CH_READER_USER} and profiles writer_profile, reader_profile are up to date"
