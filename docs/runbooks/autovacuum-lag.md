# Autovacuum lag / dead tuples

**Symptom.** Tables and indexes grow without data growth, queries slow down, plans get worse (stale statistics).

**Where to look.** `pg-indexes` → *Dead tuples / vacuum* table (dead %, last vacuum, last analyze).

**How to interpret.**
- `pg_table_stat.dead_tup_pct` > 10 %: warning; > 20 %: critical (default autovacuum threshold is 20 % + 50 rows).
- `now - last_any_vacuum_epoch` large on a table with high `spread(n_tup_upd + n_tup_del)` → autovacuum cannot keep up.
- `n_mod_since_analyze` large relative to `n_live_tup` → statistics are stale → bad plans.
- `pg_activity_grouped` rows with `max_xact_age_s` high → vacuum is blocked by an old transaction
  ([idle-in-transaction](idle-in-transaction.md)).

**Likely causes.** High update/delete rate on big tables with default scale factors, long transactions holding
the xmin horizon, autovacuum throttled (`autovacuum_vacuum_cost_limit`), too few workers.

**Actions.**
1. Remove old transactions first.
2. Per-table tuning: `ALTER TABLE ... SET (autovacuum_vacuum_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.02)`.
3. Raise `autovacuum_vacuum_cost_limit` / workers (parameter group).
4. Manual `VACUUM (ANALYZE)` in a quiet window; `pg_repack` for heavy bloat (DBA).

**Related SQL.** `sql/database_table_stat.sql`, `sql/cluster_activity_grouped.sql`.
