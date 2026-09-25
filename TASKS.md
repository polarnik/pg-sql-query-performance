# TASKS

> Each task: goal → input → output artifact → Definition of Done (DoD) → one verification command.
> Work in ≤20-min slices; after each slice append a line to `STATUS.md`.

## T0 Bootstrap docs — ✓
- Output: `PLAN.md`, `TASKS.md`, `STATUS.md`, `DECISIONS.md`.
- DoD: T1–T8 have DoD and a verification command.
- Verify: `ls PLAN.md TASKS.md STATUS.md DECISIONS.md`

## T1 Stack upgrade — ✓
- Goal: PG17 + pg_stat_statements, Telegraf 1.3x, Grafana 11, InfluxDB 1.8 run locally.
- Input: `docker-compose.yml`.
- Output: updated compose (`command: -c shared_preload_libraries=...`), `config/postgresql/monitoring_user.sql` (`GRANT pg_monitor`).
- Slices: (a) bump images + `command: -c shared_preload_libraries=pg_stat_statements`; (b) init SQL; (c) smoke test.
- DoD: all containers healthy; `pg_stat_statements` readable by the monitoring user.
- Verify: `docker compose up -d db influxdb telegraf grafana && docker compose exec db psql -U telegraf_monitoring_user -d postgres -c "select count(*) from pg_stat_statements"`

## T2 One instance, inline SQL, `.env` — ✓
- Goal: Telegraf monitors one PG17 instance with no DB-side functions, config from `.env`.
- Input: T1 stack, `config/postgresql/monitoring_*.sql` bodies.
- Output: `inputs.postgresql_extensible.conf` without `monitoring_*()` calls; `.env.example`; `.gitignore` has `.env*`.
- Slices: (a) inline activity SQL; (b) statements: text → fields, md5 tags; (c) `${PG_DSN}`, global tags.
- DoD: no `public.monitoring_` string in `config/telegraf`; `query` is not a tag key.
- Verify: `docker compose exec telegraf telegraf --test --config /etc/telegraf/telegraf.conf --config-directory /etc/telegraf/telegraf.d`

## T3 Runbook scenarios — ✓
- Goal: ~10 English runbooks (Symptom → Panel → Interpretation → Causes → Actions → Related SQL).
- Input: T2 data, PLAN "Runbook scenarios".
- Output: `docs/runbooks/*.md`.
- DoD: every scenario references ≥1 measurement from the data contracts.
- Verify: `grep -L "pg_" docs/runbooks/*.md` prints nothing.

## T4 Metrics catalog + SQL — ✓
- Goal: every measurement has tested SQL.
- Input: T3.
- Output: `docs/metrics-catalog.md`, `sql/*.sql`.
- DoD: each SQL runs as a `pg_monitor`-only user on PG17.
- Verify: `for f in sql/*.sql; do case $f in *database_*) db=demo;; *) db=postgres;; esac; docker exec -i sql_monitor_postgres psql -X -v ON_ERROR_STOP=1 -U telegraf_monitoring_user -d $db -f - < $f >/dev/null || echo FAIL $f; done`

## T5 Collection + 4 instances — ✓
- Goal: all catalog measurements land in Influx for 4 `db_instance` values.
- Input: T4 SQL.
- Output: `telegraf.d/cluster_*.conf`, `database_objects.conf`; compose `x-telegraf` anchor ×4; `.env.db1..4`.
- DoD: 4 `db_instance` tag values; series cardinality < 20k.
- Verify: `docker compose exec influxdb influx -database pg_monitoring -execute 'SHOW TAG VALUES WITH KEY = "db_instance"; SHOW SERIES CARDINALITY'`

## T6 Overview / Connections boards — ✓
- Goal: Python generator for `pg-overview`, `pg-connections`.
- Input: T5 measurements.
- Output: `dashboards/` project, 2 JSON files in provisioning dir.
- DoD: generator runs; Grafana provisioning log has no errors.
- Verify: `make -C dashboards && docker compose restart grafana && (cd dashboards && .venv/bin/python check_queries.py)` (all panels `ok`, exit 0)

## T7 Statements / Detail / Indexes boards — ✓
- Goal: `pg-statements`, `pg-statement-detail`, `pg-indexes` with drill-down.
- Input: T6 builder.
- Output: 3 JSON files + data links.
- DoD: clicking an md5 opens detail with `var-query_mask_md5`, time range and `db_instance` filled.
- Verify: `jq '..|.url? // empty' config/grafana/provisioning/dashboards/json/pg-statements.json | grep var-query_mask_md5`

## T8 K8s port — ✓
- Goal: deploy like `jcp-perftest-common`.
- Input: T7.
- Output: chart/manifests; one Telegraf deployment per instance from a values list; DSN in Secrets.
- DoD: manifests render.
- Verify: `charts/pg-telegraf/sync-files.sh --check && helm lint charts/pg-telegraf && helm template t charts/pg-telegraf | kubectl apply --dry-run=client --validate=false -f -`
