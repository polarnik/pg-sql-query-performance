# Connection exhaustion

**Symptom.** Application errors `FATAL: sorry, too many clients already`,
`FATAL: too many connections for role "..."` / `... for database "..."`, or connection-pool timeouts.

**Where to look.** `pg-connections` → *Limit usage* table (server / database / role rows), *Connections by state* time series.

**How to interpret.**
| usage | meaning |
|---|---|
| < 70 % | healthy |
| 70–90 % | warning: little headroom for bursts, deploys or failover |
| > 90 % | critical: new sessions will be rejected soon |
- Server limit = `pg_settings_limits.effective_limit` (`max_connections - superuser_reserved - reserved`).
- Per DB: `pg_db_limits.usage_pct` (`datconnlimit = -1` → server limit is used).
- Per role: `pg_role_limits.usage_pct` (`rolconnlimit = -1` → server limit is used).
- The limit that is hit first is the one with the highest `usage_pct`.

**Likely causes.**
- Pool `maxPoolSize × number of app instances` > limit (see [pool misconfiguration](pool-misconfiguration.md)).
- Leaked sessions: many `idle` / `idle in transaction` rows in `pg_activity_grouped` with a large `max_state_age_s`.
- Slow queries hold connections longer → pools grow (see [slow query regression](slow-query-regression.md)).

**Actions.**
1. Find the top `(application_name, usename)` by `cnt` in `pg_activity_grouped`.
2. If `idle` dominates → reduce pool size / `minimumIdle`, set `idle_session_timeout`.
3. If `active` dominates → fix the slow statements; add a pooler (PgBouncer / RDS Proxy).
4. Raise `max_connections` only as last resort (memory: `work_mem` × active sessions).

**Related SQL.** `sql/cluster_settings_limits.sql`, `sql/cluster_db_limits.sql`, `sql/cluster_role_limits.sql`, `sql/cluster_activity_grouped.sql`.
