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
- **D14 Statements breakdown (pg-statements):**
  - (a) Totals come from a separate measurement `pg_stmt_totals` = `pg_stat_statements` aggregated in PG by
    `(usename, datname)` over **all** entries. The breakdowns by datname and by datname+db_instance are derived in InfluxQL.
    Rejected: summing `pg_stmt_mask` (top-N only, understates totals, jumps when the top-N set changes); three
    measurements (triple collection and cardinality).
  - (b) Increase over the range = subquery `non_negative_difference(last(x))` per series and `GROUP BY time(5m)`,
    then outer `sum()` per breakdown. Not `spread()`: a stats reset or dealloc would produce huge or negative values.
  - (c) Click-to-filter = data link to the same board (`/d/pg-statements?${__url_time_range}&var-<x>=${__data.fields.<x>}`),
    other variables are kept via `${<var>:queryparam}`. Ad-hoc filters don't work with raw InfluxQL, and table
    "Filter for value" filters only one panel. New variable `usename` (multi, All = `.*`) is applied to `pg_stmt*`.
- **D15 Classic CQ chain kept and fixed** (`config/influxdb/init.sh`, used only by `pgquery`/`pgstat`):
  - (a) `host` = `${PG_INSTANCE}` (`telegraf.conf` `hostname`) instead of the container ID; every re-created container
    used to start new series (10 `host` values for 4 instances), breaking the 1m deltas and piling up archive series.
  - (b) `toplevel` added to the GROUP BY of the statement CQs (`pg_stat_statements` key = userid, dbid, queryid, toplevel).
  - (c) `query_1d`: `RESAMPLE EVERY 1h FOR 1d` (was every 10m — rescans a whole day per run, cf. issue #4 memory);
    `FOR` 3m/4m/5m for the 1m CQs (margin over `flush_interval = 60s`).
  - (d) `archive` RP on `telegraf_pg_demo` / `telegraf_pg_activity_demo`: 1000d → 200d (same horizon as D16);
    data older than 200d is dropped.
  - (e) `init.sh` is idempotent (RP: CREATE if missing else ALTER; CQ: DROP + CREATE) and can be re-run on a live
    InfluxDB: `docker exec sql_monitor_influxdb sh /docker-entrypoint-initdb.d/init.sh`. `influx -execute` parses one
    line only → statements are collapsed to one line. `DROP CONTINUOUS QUERY` on a missing CQ is a no-op in 1.8.6.
  - (f) Known, not fixed: legacy boards reference measurements that nothing writes — `pg_stat_statements_analyse`,
    `pg_stat_statements_query_md5`, `pg_stat_statements_diff` (`pgquery.json`, `pgstat.json`, `pgActivity.json`).
- **D16 Downsampling `pg_monitoring."7d"` → `"200d"` at 1h** (`config/influxdb/pg_monitoring_downsample.sh`, called by `init.sh`):
  - (a) One CQ per measurement (13), `RESAMPLE EVERY 1h FOR 2h`, explicit tag list without `host/server/db`,
    **same field names** as in `7d` → dashboards only switch the RP. RP `200d` is not DEFAULT, shard 7d.
  - (b) Counters are stored as `last()` (not as hourly increases): the existing `increase_query`
    (`non_negative_difference(last())`, D14b) works unchanged on 1h points, including resets and dealloc.
    Rejected: storing `non_negative_difference` per hour (a new field set, breaks on top-N gaps inside the CQ window).
  - (c) Gauges use `max()` so peaks are not averaged away; `pg_activity_grouped` also gets `cnt_mean`.
  - (d) `BACKFILL=1` runs the same SELECTs over the raw history in hour-aligned day chunks (a split 1h bucket would
    be overwritten by a partial `max()`). Verified: stored 1h values = direct 1h rollup of `7d`
    (`pg_stmt_totals` calls 1 581 662 = 1 581 662).
  - (e) Known limitation: at 1h resolution an increase over a range misses the part of the first bucket
    (≤ 1h of a 200d range); points arriving > 2h late are not rolled up.
  - (f) Dashboards: custom variable `rp` (`7d` default | `200d`, first variable), every query reads
    `FROM "$rp"."<measurement>"` (`builder/common.py::src`), links carry `${rp:queryparam}`. On `200d` use ranges of
    days: increases/rates need ≥ 2 hourly points. `check_queries.py` runs every panel for both RPs.
  - (g) Kubernetes: optional hook Job `influxdbInit.enabled` (default false) runs the same script against
    `influxdb.host` (`files/influxdb/` via `sync-files.sh`); the target DB must already have RP `7d`.
- **D17 ClickHouse dual write** (`config/telegraf/telegraf.d/output_clickhouse.conf`): the same 4 Telegraf services get a
  second output `[[outputs.sql]]` (`driver = "clickhouse"`) next to the unchanged `[[outputs.influxdb]]`.
  Rationale: no regression for InfluxDB / `pg-*` boards, and the two storages can be compared on the same points.
  - (a) `namepass` = the 13 `pg_monitoring` measurements; the classic-board input (D13) stays InfluxDB-only.
    `tagexclude = ["db_and_stand", "retention_policy", "host"]` on the output only: InfluxDB routing (D9) keeps working,
    `host` = `db_instance` is redundant.
  - (b) DSN `tcp://${CH_HOST}:9000?username=…&password=…&database=pg_monitoring&read_timeout=60&write_timeout=60`.
    Telegraf 1.32.3 bundles clickhouse-go v1: `clickhouse://user:pass@host` ignores the credentials
    (`default: Authentication failed`).
  - (c) `table_exists_template = "SELECT 1 FROM {TABLE} LIMIT 1"`: Telegraf never creates tables (writer has no DDL).
    An unknown column fails the whole insert of that table → tag / field names must match the schema
    (checked against `telegraf --test`).
  - (d) Image `clickhouse/clickhouse-server:24.8` (LTS); native 9000 for Telegraf and Grafana, HTTP 8123 for checks;
    ports are not published. `x-telegraf` and Grafana `depends_on: clickhouse: service_healthy`; the healthcheck logs in
    as `writer` (not only `/ping`), so Telegraf does not start before `02_users.sh` has run (cold-start restart loop).
  - (e) Batching: Telegraf `metric_batch_size` (unchanged) + `async_insert` in the writer profile. On a ClickHouse
    restart Telegraf buffers up to `metric_buffer_limit` and catches up.
- **D18 One wide typed table per measurement** (`config/clickhouse/init/01_schema.sql`, database `pg_monitoring`,
  table name = measurement name), created ahead by the init SQL (`IF NOT EXISTS`, safe to re-run).
  Rationale: typed columns, good compression and fast reads; rejected: a generic `(name, tags Map, fields Map)` table.
  - (a) Tags → `LowCardinality(String)`; fields: integer → `Int64`, float8 → `Float64`, text → `String`; types follow
    `sql/*.sql`. No `Nullable`: every column has a `DEFAULT` (`0` / `''`), so a missing field or empty
    `datname` / `usename` is stored as the default.
  - (b) Codecs: `time` `DoubleDelta`, integers `T64`, floats `Gorilla`, text `ZSTD(3)`, all + `ZSTD`.
  - (c) `PARTITION BY toYYYYMMDD(time)`; `ORDER BY` starts with `db_instance` + the dashboard filter columns, then
    `time` (settings snapshots: `(db_instance, time)`; objects: `(db_instance, datname, schemaname, relname[, indexrelname], time)`).
  - (d) `pg_stmt_text` = `ReplacingMergeTree(time) ORDER BY (db_instance, query_md5)`, no partitioning: only the latest
    text per md5 is kept; reads use `argMax(…, time)` / `FINAL`.
  - (e) Raw data only, `TTL toDateTime(time) + INTERVAL 30 DAY`; no rollups / materialized views (unlike D16).
    Change with `ALTER TABLE … MODIFY TTL`.
- **D19 Three ClickHouse users, least privilege** (`config/clickhouse/init/02_users.sh`, SQL-driven access control):
  - (a) `admin` = container user (`CLICKHOUSE_USER/PASSWORD` from `CH_ADMIN_USER/PASSWORD`,
    `CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1`); replaces the ClickHouse `default` user; full access incl. access management.
  - (b) `writer` (Telegraf): `GRANT INSERT, SELECT ON pg_monitoring.*` (SELECT for `table_exists_template`), profile
    `writer_profile`: `async_insert=1`, `wait_for_async_insert=1`, `async_insert_busy_timeout_ms=1000`. No DDL / DROP.
  - (c) `reader` (Grafana): `GRANT SELECT ON pg_monitoring.*`, profile `reader_profile`: `readonly=2 CONST`,
    `max_execution_time=30 MAX 60`, `max_memory_usage=2e9`, `max_result_rows=1e6`, `max_rows_to_read=1e9`.
  - (d) Passwords from env: `.env.example` (local defaults) → git-ignored `.env.clickhouse` (ClickHouse, Grafana) /
    `.env.dbN` (Telegraf). The script is idempotent (`CREATE … IF NOT EXISTS` + `ALTER`, `REVOKE ALL` + `GRANT`),
    so a re-run also applies new passwords.
  - (e) Grafana datasource `config/grafana/provisioning/datasources/clickhouse-pg-monitoring.yml`: uid `pg-monitoring-ch`,
    type `grafana-clickhouse-datasource` (`GF_INSTALL_PLUGINS`, downloaded at start → needs internet), native 9000,
    user `reader`, `queryTimeout = 55`: the plugin sends `max_execution_time = queryTimeout + 4`, and 56+ exceeds the
    reader cap of 60.
- **D20 `ch-*` boards** (`dashboards/ch_*.py` + `dashboards/builder/clickhouse.py`), the `pg-*` boards are not touched:
  - (a) UIDs `ch-overview`, `ch-connections`, `ch-statements`, `ch-statement-detail`, `ch-indexes`; titles
    `PostgreSQL (ClickHouse) / …`; tags `ch-runbooks`, `clickhouse` (own runbook dropdown). Same panels, variables
    (`db_instance`, `datname`, `usename`, `query_mask_md5` / `query_md5`), runbook rows and drill links as `pg-*`;
    no `rp` variable (no rollups, D18e).
  - (b) `ClickHouseSQL` Dataquery: `{rawSql, editorType: "sql", format, queryType}`, `format` 0 = timeseries, 1 = table.
    Filters: `$__timeFilter(time)`, `$__conditionalAll(col IN (${var:singlequote}), $var)` (no commas inside),
    textbox variables via `match(col, '^(…)$')`.
  - (c) Counter increase (replaces `spread()` / `non_negative_difference`, D4, D14b) = sum of the positive steps per
    series (`lagInFrame`) → never negative. Per-entry counters count the new value after a reset; `pg_stmt_totals`
    sums ignore drops (dealloc, as in D14b). Rates per bucket use the same steps divided by the time delta.
  - (d) Inner aliases are named `c_*`: ClickHouse resolves an alias equal to a column name inside other expressions
    (code 184, nested aggregate).
  - (e) `check_queries.py --clickhouse` runs every variable and panel query through Grafana `/api/ds/query` on
    `pg-monitoring-ch` (= as `reader`), once with all variables = All and once with the first value of each.
- **D21 One Telegraf for N instances, inputs rendered at start** (supersedes D6 and the env chain of D12; D15a `host`
  now comes from the input tags): `config/telegraf/entrypoint.sh` + templates `config/telegraf/inputs.d/*.conf`.
  - (a) Why: `inputs.postgresql_extensible` takes one `address` and Telegraf config has no loops, so N instances need
    N copies of every input. Options: **A** render the templates per instance at start (chosen); **B** N telegraf
    processes in one container (`DBn_*` → `PG_*`): configs unchanged, but still N agents, a health port each, a dead
    process is hard to notice; **C** hand-written copies (~40 blocks with `${DB1_DSN}` … `${DB4_DSN}`): no script,
    but heavy duplication and a new metric is easily forgotten for one instance. A = one process, one config to edit,
    a new instance is three env lines.
  - (b) Env contract (one file: `.env.example` → gitignored `.env.dbs`): `PG_INSTANCES=DB1,…` + per id
    `<ID>_INSTANCE`, `<ID>_DSN`, `<ID>_APP_DSN`; `PG_ENV`, `INFLUX_DB_*`, `CH_*` once. A missing variable, an invalid
    or duplicate id stops the container with the variable name in the log.
  - (c) Rendering = `sed` of variable **names** only (`${PG_DSN}` → `${DB1_DSN}`, `${PG_APP_DSN}`, `${PG_INSTANCE}`)
    into a flat dir (`db1__cluster_activity.conf`, …; tmpfs in compose, `emptyDir` in Helm), plus a copy of the static
    `telegraf.d/*.conf` (outputs). Telegraf expands the values → no password on disk. `--render-only` / `--test`.
  - (d) Tags unchanged for dashboards: `db_instance` and `host` moved from `global_tags` / `agent.hostname` into every
    `[inputs.postgresql_extensible.tags]` (= `${PG_INSTANCE}`), `omit_hostname = true`; `server` = `outputaddress`;
    `env` stays global. Verified: InfluxDB `db_instance` and classic `host` = `demo-db1..4`, ClickHouse 4 `db_instance`.
  - (e) Helm: one Deployment; instance N of `instances[]` → id `DB<N>`, `DB<N>_DSN` / `DB<N>_APP_DSN` via
    `secretKeyRef` to the existing per-instance Secrets (keys `PG_DSN` / `PG_APP_DSN`, values compatible).
    ClickHouse output stays compose-only (`sync-files.sh` skips `output_clickhouse.conf`, like classic boards).
  - (f) Trade-offs: 4× metrics on one agent → `metric_buffer_limit` 40000, chart limit 512Mi; a restart stops
    collection for all instances at once; a broken DSN only fails its own inputs (per-input errors, `statement_timeout`).
- **D22 `env` on the generated boards: filter + series key** (`dashboards/builder/common.py`, `builder/clickhouse.py`,
  the 10 `pg-*` / `ch-*` generators; the hand-made `pgActivity` / `pgquery` / `pgstat` are not touched).
  - (a) Why: the `env` tag / column (`<ID>_ENV`, default `PG_ENV`, D21) was collected but ignored by the boards, so two
    envs with the same `db_instance` name were merged (counters summed, `last()` mixed).
  - (b) Variable `Env` (multi, All = `.*`), first after `Retention`; `Instance` / `Database` / `User` are narrowed by it
    (`WHERE env =~ /^$env$/`, ClickHouse `$__conditionalAll(env IN (...))`).
  - (c) Series key: `env` prefixes every `GROUP BY` / `series` / `group_by` tuple (`common.SERIES`, `OBJ`, `ACTIVITY`,
    …), so with Env = All every table has an `env` column and rows of different envs are never summed; time series
    are split per env (legend `<tag> (<env>)` on pg-statements).
  - (d) Links: `env` is in `FILTER_VARS` (self-filter links keep `${env:queryparam}`), drill-down links pass
    `var-env=${__data.fields.env}`. Dashboard UIDs unchanged.
  - (e) `check_queries.py` substitutes `$env = .*` and now also runs the `pg-*` variable queries.
- **D23 Env comparison boards** (`dashboards/builder/compare.py`, `compare_*.py` → `pg-cmp-*`, `ch_compare_*.py` →
  `ch-cmp-*`; Tables, Indexes, Statements, Schema drill, separate boards linked by the tag `pg-env-compare` /
  `ch-env-compare`).
  - (a) Layout: the same Instance in two envs, Env A left / Env B right (two `w=12` tables per topic), sorted
    descending by the main metric; full-width diff tables: "only in A / B", Δ (B − A, `delta_pct` = Δ / A, sorted by
    |Δ|), changed index flags.
  - (b) Variables: `env_a` / `env_b` single value, `env_b` sorted descending (default ≠ `env_a`); `db_instance`
    single value (InfluxDB: instances of env A; ClickHouse: of env A, the ones of both envs first); `datname` multi,
    default All; Schema drill: `schemaname` single + `relname` regex textbox. Table / schema cells link to the drill.
  - (c) InfluxDB has no joins: query A (`env = '$env_a'`, columns `*_a`) and B (`*_b`) group by the same tags
    without env; Grafana drops Time (the `last()` timestamp differs), outer-merges them (`merge`), then
    `filterByValue` (isNull → only in A / B), `calculateField` (Δ, Δ %, |Δ|), `sortBy`. ClickHouse: one SQL, per-object
    rows of both envs → `anyIf(x, env = A)` / `countIf` (`compare.pair_query`), no transformations.
  - (d) Activity is normalized as `share_pct` = share of the env total (loads differ): InfluxDB joins a per-env
    total query on `env` (`joinByField` inner), ClickHouse `x / sum(x) OVER ()`.
  - (e) Statements are matched by `query_mask_md5`, summed over users (roles may differ); ClickHouse takes the full
    mask text from `pg_stmt_text`. md5 cells open `*-statement-detail` with `var-env` of that side.
  - (f) Limits: top-N collection (300 tables / 500 indexes / 200 statements) → "only in" can mean "outside the
    top-N"; objects dropped inside the range still appear. Grafana-side transformations are not covered by
    `check_queries.py` (it runs the queries only); `CHECK_VARS=env_a=…,env_b=…,db_instance=…` pins the single-value
    variables to a pair with data on both sides, `--only=cmp` limits the run.
