# DECISIONS (append-only)

## Assumptions (defaults used until confirmed)
- **A1** Targets are AWS RDS PG17 (because of the `rdsadmin` filter) → no superuser, use `pg_monitor`.
- **A2** "4 databases" = 4 separate PG instances, each with 1 app DB. If it is 1 instance with 4 DBs,
  cluster-wide metrics are collected once, per-DB metrics 4 times.
- **A3** InfluxDB stays at 1.8 (InfluxQL); upgrading to 1.11/2.x is out of scope.
- **A4** Grafana is upgraded to 11.x (required by grafana-foundation-sdk).
- **A5** Telegraf is upgraded to 1.3x (1.18 is from 2021).

## Decisions
- **D0 Stack upgrade first:** `postgres:17` (`shared_preload_libraries=pg_stat_statements`), `telegraf:1.3x`,
  `grafana:11.x`, InfluxDB 1.8. Demo DB (`demo-small-20170815.sql`) + JMeter load stay as local load generator.
- **D1 Inline SQL** replaces each `monitoring_*.sql` function body; use PG17 column names.
- **D2 Cardinality control:** tags = `db_instance, datname, usename, query_md5/query_mask_md5`; text is a **field**;
  statements = top-N (default 200) by cumulative `total_exec_time` ∪ top-N by `calls`;
  separate low-frequency (30 min) `pg_stmt_text` measurement for md5 → full text.
- **D3 Two statement measurements:** `pg_stmt` (per queryid, carries `query_mask_md5`) and `pg_stmt_mask` (GROUP BY mask).
- **D4 Counters are cumulative:** tables use `spread()` / `last()-first()` over `$timeFilter`;
  time series use `non_negative_derivative(...,1s)`; resets tracked through `pg_stmt_info.stats_reset`.
- **D5 Dashboards as code in Python** (grafana-foundation-sdk) generating JSON into
  `config/grafana/provisioning/dashboards/json/`; Jsonnet (youtrack-sitespeed-tests) is reference only.
- **D6 One Telegraf service per DB instance** via compose `x-telegraf` anchor + `env_file: .env.<instance>`;
  identical `telegraf.d/` mounted read-only.
- **D7 Split inputs by scope & interval:** `cluster_*.conf` (activity 15–30s, settings 5m, statements 5m) connect to
  the maintenance DB; `database_*.conf` (tables/indexes 5m) connect to each app DB.
- **D8 Stable dashboard UIDs:** `pg-overview`, `pg-connections`, `pg-statements`, `pg-statement-detail`, `pg-indexes`.
- **D9 Influx routing:** every input carries tag `db_and_stand` (value `${PG_INFLUX_DB}`) because the output uses
  `database_tag = "db_and_stand"`.
- **D10 One Influx DB for new metrics:** all catalog measurements go to `pg_monitoring` (RP `7d`, `INFLUX_DB_MONITORING`),
  Grafana datasource uid `pg-monitoring`. Legacy DBs `telegraf_pg_demo` / `telegraf_pg_activity_demo` only receive the
  classic-boards input (see D13).
- **D11 SQL single source:** Telegraf inputs load `sql/*.sql` via `script = "/etc/telegraf/sql/..."`. Inline SQL in
  Telegraf config goes through env substitution (`$$` becomes `$`, `${X}` is replaced) — avoid inline SQL.
- **D12 Per-instance env:** `.env.example` (defaults) → `config/telegraf/env/dbN.env` (committed, `PG_INSTANCE`) →
  `.env.dbN` (gitignored, real DSNs). `PG_DSN` = maintenance DB (cluster scope), `PG_APP_DSN` = app DB (database scope).
  `statement_timeout=5000` in the DSN is applied by pgx as a runtime parameter (verified: `5s`).
- **D13 No inline SQL, no legacy.d:** every `[[inputs.postgresql_extensible.query]]` uses `script = "/etc/telegraf/sql/<file>.sql"`
  (`sqlquery` is not used anywhere). The classic-board input moved from `config/telegraf/legacy.d/` to
  `config/telegraf/telegraf.d/cluster_classic_boards.conf` + `sql/cluster_stat_*.sql`; it runs for all instances in
  docker-compose (identical Telegraf services) and is excluded from `charts/pg-telegraf` by `sync-files.sh`.
