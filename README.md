# pg-sql-query-performance
Мониторинг, анализ и оптимизация производительности SQL-запросов к PostgreSQL. Описание и демонстрация

Monitoring, analyzing, and optimizing the performance of PostgreSQL SQL queries. Description and demonstration

## Start

```bash
docker-compose up
```

Open Grafana: [http://localhost:3000](http://localhost:3000)

## PostgreSQL 17 monitoring runbooks (Telegraf → InfluxDB → Grafana)

No functions are created in the monitored databases: all metrics are plain `SELECT`s from `sql/*.sql`
run by a `pg_monitor`-only user.

```bash
docker compose up -d clickhouse db influxdb telegraf telegraf-db2 telegraf-db3 telegraf-db4 grafana
make -C dashboards                                  # generate pg-* + ch-* dashboards (Python 3.13, grafana-foundation-sdk)
(cd dashboards && .venv/bin/python check_queries.py) # every panel query runs through Grafana
```

- Real instances: copy `.env.example` to `.env.db1..4` (gitignored) and set `PG_DSN` / `PG_APP_DSN`.
- Dashboards: `pg-overview` → `pg-connections`, `pg-statements` → `pg-statement-detail`, `pg-indexes` (InfluxDB);
  the same set as `ch-*` on ClickHouse (see [ClickHouse](#clickhouse-dual-write-decisionsmd-d17d20)).
- ClickHouse settings: `CH_*` variables in `.env.example`, real passwords in the gitignored `.env.clickhouse`.
- Docs: `PLAN.md`, `TASKS.md`, `STATUS.md`, `DECISIONS.md`, `docs/metrics-catalog.md`, `docs/runbooks/`.
- Kubernetes: `charts/pg-telegraf` (InfluxDB output only, no ClickHouse).
- Retention (`DECISIONS.md` D15, D16): `pg_monitoring."7d"` keeps raw points, `pg_monitoring."200d"` keeps 1h rollups
  (continuous queries). Dashboards have a `Retention` variable (`7d` / `200d`).
- `config/influxdb/init.sh` runs only on an empty InfluxDB volume. To apply RPs / CQs to an existing InfluxDB
  (idempotent, safe to re-run):

```bash
docker compose up -d influxdb                                                          # mounts the downsampling script
docker exec sql_monitor_influxdb sh /docker-entrypoint-initdb.d/init.sh                # all DBs, RPs and CQs
docker exec -e BACKFILL=1 sql_monitor_influxdb sh /opt/influxdb-init/pg_monitoring_downsample.sh  # + roll up the raw 7d
```

- External InfluxDB (Helm): `--set influxdbInit.enabled=true` (optionally `influxdbInit.backfill=true`,
  `influxdbInit.existingSecret=<secret with INFLUX_USERNAME / INFLUX_PASSWORD>`) runs the same script as a
  post-install/upgrade hook Job against `influxdb.host`. Or run it manually:
  `INFLUX_ARGS="-host <influx> -port 8086" sh config/influxdb/pg_monitoring_downsample.sh`.

### ClickHouse (dual write, `DECISIONS.md` D17–D20)

Telegraf writes the same 13 `pg_monitoring` measurements to InfluxDB **and** ClickHouse (`[[outputs.sql]]`,
`config/telegraf/telegraf.d/output_clickhouse.conf`). `docker compose up` starts the `clickhouse` service
(`clickhouse/clickhouse-server:24.8`, volume `sql-monitor-clickhouse-data`) automatically: on an empty volume
`config/clickhouse/init/01_schema.sql` creates the 13 tables (30-day TTL) and `02_users.sh` the users.
Telegraf and Grafana wait until ClickHouse is healthy.

```bash
docker compose up -d clickhouse db influxdb telegraf telegraf-db2 telegraf-db3 telegraf-db4 grafana
make -C dashboards                                                 # also writes ch-*.json
(cd dashboards && .venv/bin/python check_queries.py --clickhouse)  # every ch-* panel SQL as reader, via Grafana
curl -s -u admin:admin http://localhost:3000/api/datasources/uid/pg-monitoring-ch/health
docker exec sql_monitor_clickhouse clickhouse-client --user admin --password admin -q "SHOW TABLES FROM pg_monitoring"
```

| user | used by | rights |
|---|---|---|
| `admin` (`CH_ADMIN_USER`) | operator | everything, incl. access management (replaces `default`) |
| `writer` (`CH_WRITER_USER`) | Telegraf, native port 9000 | `INSERT, SELECT` on `pg_monitoring.*`, async inserts |
| `reader` (`CH_READER_USER`) | Grafana datasource `pg-monitoring-ch` | `SELECT` on `pg_monitoring.*`, `readonly=2`, ≤ 60 s / 2 GB / 1M rows |

- Env: `CH_HOST`, `CH_ADMIN_USER` / `CH_ADMIN_PASSWORD`, `CH_WRITER_USER` / `CH_WRITER_PASSWORD`,
  `CH_READER_USER` / `CH_READER_PASSWORD`. `.env.example` has local defaults only; put real passwords into the
  gitignored `.env.clickhouse` (ClickHouse, Grafana) and `.env.db1..4` (Telegraf, same writer password).
- Users are created only on the first start (empty volume). To apply changed passwords to an existing volume:
  `docker exec -e CLICKHOUSE_USER=admin -e CLICKHOUSE_PASSWORD=admin sql_monitor_clickhouse bash /docker-entrypoint-initdb.d/02_users.sh`
  (idempotent; use your `CH_ADMIN_*` values).
- Dashboards (tags `clickhouse`, `ch-runbooks`; titles `PostgreSQL (ClickHouse) / …`): `ch-overview` → `ch-connections`,
  `ch-statements` → `ch-statement-detail`, `ch-indexes`. Same variables and drill-down as the `pg-*` boards;
  ClickHouse keeps raw data for 30 days, so there is no `Retention` variable.
- Grafana downloads the `grafana-clickhouse-datasource` plugin at start (`GF_INSTALL_PLUGINS`): it needs internet
  access, otherwise the `ch-*` boards show "plugin not found".
- ClickHouse ports 8123 / 9000 are not published; use `docker exec … clickhouse-client` or uncomment `ports`.

## Нагрузка на jmeter-java-dsl (Kotlin)

Те же сценарии, что в `src/test/jmeter/sql_demo_test.jmx` (эталон, профиль `jmeter` не менялся), описаны на
[jmeter-java-dsl](https://abstracta.github.io/jmeter-java-dsl/guide/#jdbc-and-databases-interactions)
в `src/test/kotlin/qa/load/sql`:

| Файл | Что там |
|---|---|
| `LoadProfile.kt` | **интенсивность**: множитель к `-Dtps` для каждого сценария |
| `scenarios/Qpt03SeqScan.kt … Qpt11Technics.kt`, `QptTransaction.kt` | SQL-запросы сценария (название + текст) |
| `pools/Pools.kt` | пулы: `ApplicationName`, пользователь, `poolMax`, autocommit |
| `SqlDemoPlan.kt` | сборка плана: thread group на сценарий + пейсинг |

С jmx совпадают `ApplicationName` и пользователи пулов, тексты SQL байт в байт (`queryid` в `pg_stat_statements`),
типы запросов, названия запросов и транзакций, Backend Listener InfluxDB.

#### Интенсивность

Каждый сценарий (Stable) работает в своей thread group, одна итерация = одна транзакция (все запросы сценария по разу).
Темп сценария = `tps × множитель` транзакций в секунду на всю группу (Constant Throughput Timer).
Все множители `1.0` = как в jmx; `0.1` = в 10 раз реже; `0` = сценарий выключен.
Менять можно в `LoadProfile.kt` или без правки кода: `-Drate.qpt_11_technics=0.1 -Drate.qpt_04_indexscan=5`.
Потолок сценария — `thread_count / время транзакции` (qpt_11 ~0.5 с × 50 потоков ≈ 100 TPS).

```bash
mvn verify -P jmeter-dsl,Stable -Dtps=1.0          # сценарии qpt_03..qpt_11 + transaction + пул qpt_idle
mvn verify -P jmeter-dsl,MaxPerf                   # MaxPerf
docker compose --profile dsl up jmeter-dsl         # внутри sql-monitor-network, метрики в InfluxDB
```

Из IDE / с хоста (PostgreSQL на `localhost:5432`, порт InfluxDB наружу не открыт):

```bash
mvn -P jmeter-dsl test -Dtest=SqlDemoSmokeTest -Ddb.host=localhost -Dinfluxdb.enabled=false   # каждый запрос 1 раз, 0 ошибок
mvn -P jmeter-dsl,Stable verify -Dduration=60 -Dthread_count=5 -Dtps=1.0 -Ddb.host=localhost -Dinfluxdb.enabled=false
mvn -P jmeter-dsl,Stable test -Ddsl.exportOnly=true   # только сохранить target/jmeter-dsl/sql_demo_test.dsl.jmx
```

Параметры: `isStable`, `isMaxPerf`, `duration` (секунды), `tps`, `thread_count`, `title`, `testId` (как в jmx),
`rate.<id сценария>` (множитель, см. выше), `db.host` (`sql_monitor_postgres`), `db.port`, `db.name`, `db.password`,
`influxdb.host/port/database`, `influxdb.enabled`.
Результаты: `target/jmeter-dsl/results/*.jtl`, HTML-отчёт `target/jmeter-dsl/report/`.


## Stop

```bash
docker-compose stop
```

## Remove

```bash
docker-compose down -v
```

## Docs

Codefest 11 : https://polarnik.github.io/pg-sql-query-performance/

## FAQ

Если при сборке проекта будет ошибка

> failed to solve with frontend dockerfile.v0: failed to create LLB definition: failed to authorize: ...

То надо в консоли (в bash) выполнить установку переменных окружения:

```bash
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
```

Источник ответа: https://stackoverflow.com/questions/64221861/failed-to-resolve-with-frontend-dockerfile-v0

DOCKER_BUILDKIT отключается, так как в данном проекте не планируется размещать 
контейнер sql_monitor_jmeter в приватном или публичном docker registry.
https://docs.docker.com/develop/develop-images/build_enhancements/

И при выполнении команды `docker build` просто соберется Docker-контейнер, без публикации куда-то.

COMPOSE_DOCKER_CLI_BUILD отключается, чтобы при выполнении docker-compose build также не выполнялась публикация куда-либо.
https://www.docker.com/blog/faster-builds-in-compose-thanks-to-buildkit-support/


