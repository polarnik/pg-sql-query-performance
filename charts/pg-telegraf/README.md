# pg-telegraf

Telegraf collectors for PostgreSQL 17 (one Deployment per instance, identical `telegraf.d` + `sql/`)
and the generated `pg-*` Grafana dashboards. Same layout as the charts in `jcp-perftest-common/charts/`.

`files/` is a copy of the docker-compose config that was tested locally — never edit it by hand:

```shell
make -C dashboards                       # regenerate dashboards JSON
charts/pg-telegraf/sync-files.sh         # copy config/telegraf, sql/, dashboards into files/
charts/pg-telegraf/sync-files.sh --check # CI: fail if files/ is stale
```

Secrets (one per instance, keys `PG_DSN` = maintenance DB, `PG_APP_DSN` = application DB):

```shell
kubectl create secret generic pg-telegraf-db1 \
  --from-literal=PG_DSN='postgres://telegraf_monitoring_user:***@db1:5432/postgres?sslmode=require&statement_timeout=5000' \
  --from-literal=PG_APP_DSN='postgres://telegraf_monitoring_user:***@db1:5432/app?sslmode=require&statement_timeout=5000'
```

Values: `instances[]` (`name` → `db_instance` tag, `existingSecret` or dev-only `dsn`/`appDsn`),
`influxdb.host` / `influxdb.database`, `env`, `dashboards.enabled` (ConfigMap with `grafana_dashboard: "1"`).
The Grafana datasource must have uid `pg-monitoring` (see `config/grafana/provisioning/datasources/influxdb-pg-monitoring.yml`).

Verify:

```shell
helm lint charts/pg-telegraf
helm template t charts/pg-telegraf | kubectl apply --dry-run=client --validate=false -f -
```
