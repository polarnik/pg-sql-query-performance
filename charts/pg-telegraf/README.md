# pg-telegraf

One Telegraf Deployment for all monitored PostgreSQL 17 instances (`instances[]`, `DECISIONS.md` D21)
and the generated `pg-*` Grafana dashboards. Same layout as the charts in `jcp-perftest-common/charts/`.

At start `files/entrypoint.sh` renders the input templates `files/inputs.d/*.conf` (ConfigMap `<release>-inputs`)
once per instance into the `emptyDir` `/etc/telegraf/rendered.d` (works with `readOnlyRootFilesystem`) and starts one
`telegraf`. Instance N of the list gets the env `DB<N>_INSTANCE` (= `name`), `DB<N>_DSN` / `DB<N>_APP_DSN`
(`secretKeyRef` to the keys `PG_DSN` / `PG_APP_DSN` of its Secret) and the id `DB<N>` in `PG_INSTANCES`.
Rendered files keep `${DB1_DSN}` references, Telegraf expands them, so no password is written to disk.

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

New instance: create its Secret and add `- name: db2` / `existingSecret: pg-telegraf-db2` to `instances`;
`helm upgrade` restarts the single pod (annotation `checksum/instances`). Names must be unique.
More instances = more metrics on one agent: raise `resources` (default limit 512Mi).

Values: `instances[]` (`name` → `db_instance` / `host` tag, optional `env` → `env` tag, `existingSecret` or dev-only
`dsn`/`appDsn`), `influxdb.host` / `influxdb.database`, `env` (default `env` tag of the instances without their own),
`dashboards.enabled` (ConfigMap with `grafana_dashboard: "1"`).
The Grafana datasource must have uid `pg-monitoring` (see `config/grafana/provisioning/datasources/influxdb-pg-monitoring.yml`).

Verify:

```shell
helm lint charts/pg-telegraf
helm template t charts/pg-telegraf | kubectl apply --dry-run=client --validate=false -f -
helm template t charts/pg-telegraf --set 'instances[1].name=db2,instances[1].existingSecret=pg-telegraf-db2' \
  | grep -A1 -E 'name: (PG_INSTANCES|DB[0-9]+_)'   # one Deployment, DB1_* + DB2_*
```
