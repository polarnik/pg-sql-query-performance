# Pool misconfiguration

**Symptom.** Many connections are open but few are `active`; connection limits are approached although load is low.

**Where to look.** `pg-connections` → *Grouped connections* table grouped by `application_name, usename, state`.

**How to interpret.**
- Ratio `idle / (active + idle)` per `application_name` in `pg_activity_grouped`:
  > 80 % with total `cnt` > 50 → the pool is oversized.
- `max_backend_age_s` very small and churning → pool does not reuse connections (connect-per-request).
- `pg_role_limits.current` close to `effective_conn_limit` for a single application role.
- `application_name = '(none)'` → clients do not set it; ask teams to set `ApplicationName` in the JDBC URL.

**Likely causes.**
- `maximumPoolSize` × replicas larger than the DB can serve; `minimumIdle = maximumPoolSize`.
- Several pools per service (per tenant / per datasource).
- No pooler between many short-lived clients and the DB.

**Actions.**
1. Size pools: roughly `cores × 2–4` active connections per DB instance in total, split across services.
2. Set `minimumIdle` lower than `maximumPoolSize`, `idleTimeout` / `maxLifetime` shorter than server timeouts.
3. Introduce PgBouncer / RDS Proxy for many small clients.
4. Set a `rolconnlimit` per application role to protect other applications.

**Related SQL.** `sql/cluster_activity_grouped.sql`, `sql/cluster_role_limits.sql`.
