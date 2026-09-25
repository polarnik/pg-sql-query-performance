# Lock waits / blocking

**Symptom.** Latency spikes, requests hang, `lock timeout` / deadlock errors.

**Where to look.** `pg-overview` → *Blocked sessions* stat + time series; `pg-connections` → *Grouped connections*
filtered by `wait_event_type = 'Lock'`.

**How to interpret.**
- `pg_locks_blocked.blocked` > 0 for more than one sample (15 s) → real contention.
- `pg_locks_blocked.max_wait_s` > 5 s: warning; > 30 s: critical.
- `blocking` small and `blocked` large → one long transaction blocks many (lock queue).
- `pg_db_stat.deadlocks` rate > 0 → deadlocks happen; check application lock ordering.

**Likely causes.**
- Long transactions holding row locks (see [idle-in-transaction](idle-in-transaction.md)).
- DDL (`ALTER TABLE`, `CREATE INDEX` without `CONCURRENTLY`) during load.
- Hot rows updated by many sessions (counters, status tables).
- Inconsistent lock ordering → deadlocks.

**Actions.**
1. Find blockers (DBA): `SELECT pid, pg_blocking_pids(pid), state, query FROM pg_stat_activity WHERE wait_event_type = 'Lock';`
2. Terminate the root blocker if it is idle in transaction.
3. Run DDL with `lock_timeout` and `CONCURRENTLY`; schedule outside load windows.
4. Redesign hot-row updates (batching, append-only, `SKIP LOCKED` queues).

**Related SQL.** `sql/cluster_locks_blocked.sql`, `sql/cluster_activity_grouped.sql`, `sql/cluster_db_stat.sql`.
