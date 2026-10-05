# Temp file spills

**Symptom.** Sorts / hash joins / aggregates are slow, disk write IO spikes, `temp_bytes` grows.

**Where to look.** `pg-overview` → *Temp bytes / files* per database; `pg-statements` → *Top masks by temp_blks_written*.

**How to interpret.**
- `pg_db_stat.temp_bytes` / `temp_files` rate > 0 under normal OLTP load is a smell; sustained MB/s is critical.
- Masks with `spread(temp_blks_written)` > 0 in `pg_stmt_mask` are the statements that spill (1 block = 8 KiB).
- `pg_settings_limits.work_mem_bytes` is the per-operation memory limit before spilling.

**Likely causes.** Large `ORDER BY` / `DISTINCT` / `GROUP BY` / hash joins without selective filters,
missing index for ordering, `work_mem` too small for analytical queries.

**Actions.**
1. `EXPLAIN (ANALYZE, BUFFERS)` the spilling mask: look for `Sort Method: external merge` / `Batches > 1`.
2. Add an index that provides the order or reduces rows early; add `LIMIT` / pagination.
3. Raise `work_mem` only for the specific role / session (`ALTER ROLE ... SET work_mem`), not globally.

**Related SQL.** `sql/cluster_db_stat.sql`, `sql/cluster_stmt_mask.sql`, `sql/cluster_settings_limits.sql`.
