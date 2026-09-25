# PostgreSQL runbooks

Each runbook follows one template and is mirrored as a collapsed **Runbook** row on its dashboard.

```
Symptom → Where to look (dashboard / panel) → How to interpret (thresholds)
        → Likely causes → Actions → Related SQL
```

Dashboards (stable UIDs, see `DECISIONS.md` D8): `pg-overview`, `pg-connections`, `pg-statements`,
`pg-statement-detail`, `pg-indexes`. Measurements: `docs/metrics-catalog.md`.

| # | Runbook | Main measurements | Dashboard |
|---|---|---|---|
| 1 | [Connection exhaustion](connection-exhaustion.md) | `pg_settings_limits`, `pg_db_limits`, `pg_role_limits`, `pg_activity_grouped` | pg-connections |
| 2 | [Idle-in-transaction leaks](idle-in-transaction.md) | `pg_activity_grouped`, `pg_db_stat` | pg-connections |
| 3 | [Pool misconfiguration](pool-misconfiguration.md) | `pg_activity_grouped`, `pg_role_limits` | pg-connections |
| 4 | [Lock waits / blocking](lock-blocking.md) | `pg_locks_blocked`, `pg_activity_grouped`, `pg_db_stat` | pg-overview |
| 5 | [Slow query regression](slow-query-regression.md) | `pg_stmt_mask`, `pg_stmt`, `pg_stmt_text` | pg-statements → pg-statement-detail |
| 6 | [Cache hit drop / high reads](cache-hit-drop.md) | `pg_db_stat`, `pg_stmt_mask` | pg-overview, pg-statements |
| 7 | [Temp file spills](temp-file-spills.md) | `pg_db_stat`, `pg_stmt_mask`, `pg_settings_limits` | pg-overview, pg-statements |
| 8 | [Unused / missing indexes](unused-missing-indexes.md) | `pg_index_stat`, `pg_table_stat` | pg-indexes |
| 9 | [Autovacuum lag / dead tuples](autovacuum-lag.md) | `pg_table_stat`, `pg_activity_grouped` | pg-indexes |
| 10 | [pg_stat_statements reset / dealloc](stat-statements-reset.md) | `pg_stmt_info`, `pg_settings_limits` | pg-statements |

Conventions:
- Counters are cumulative → "over the range" means `spread()` in InfluxQL; rates use `non_negative_derivative(...,1s)`.
- Thresholds are starting points for a perf-test stand; tune per system and record changes in `DECISIONS.md`.
