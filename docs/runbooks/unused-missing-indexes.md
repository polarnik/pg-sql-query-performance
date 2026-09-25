# Unused / missing indexes

**Symptom.** Slow reads on large tables (missing index) or slow writes / high WAL and storage (too many unused indexes).

**Where to look.** `pg-indexes` → *Unused indexes* table, *Seq-scan-heavy tables* table, *Index size* column.

**How to interpret.**
- Unused index: `spread(pg_index_stat.idx_scan) = 0` over a representative range (a full load test or ≥ 7 days),
  `is_unique = 0`, `is_primary = 0`; `last_idx_scan_epoch` old or 0. Sort by `index_bytes`.
- Missing index candidate: large `pg_table_stat.total_bytes` with high `spread(seq_tup_read)` and
  `spread(seq_scan)` ≫ `spread(idx_scan)`.
- `is_valid = 0` → a failed `CREATE INDEX CONCURRENTLY`; the index costs writes but is never used.
- Stats are per database and per instance (replicas have their own counters).

**Likely causes.** Indexes created for old features / ORM defaults, duplicate indexes (same leading columns),
new query patterns without a supporting index.

**Actions.**
1. Unused: confirm on all replicas, then `DROP INDEX CONCURRENTLY` (keep a rollback script).
2. Invalid: `DROP INDEX CONCURRENTLY` and re-create.
3. Missing: find the masks touching the table on `pg-statements` → `EXPLAIN` → `CREATE INDEX CONCURRENTLY`.

**Related SQL.** `sql/database_index_stat.sql`, `sql/database_table_stat.sql`.
