# Slow query regression

**Symptom.** Response time of an endpoint grows; DB CPU / IO grows without a matching increase in traffic.

**Where to look.** `pg-statements` → *Top masks* table (sorted by total time over the range) →
click `query_mask_md5` → `pg-statement-detail` (variants by `query_md5`, full text, calls / time series).

**How to interpret.**
- Over the range: `spread(total_exec_time)` = time spent, `spread(calls)` = executions,
  mean = `spread(total_exec_time) / spread(calls)` (ms).
- Compare the same mask for two ranges (before / after release): mean ↑ with calls ≈ → plan / data regression;
  calls ↑ with mean ≈ → more traffic or an N+1 pattern.
- `variants` of a mask ≫ 1 → the same statement shape is produced with different IN-list sizes etc.
- `shared_blks_read` ↑ → data no longer fits the cache ([cache hit drop](cache-hit-drop.md));
  `temp_blks_written` ↑ → sorts / hashes spill ([temp file spills](temp-file-spills.md)).
- `rows / calls` ↑ → the query returns more data (missing filter / pagination).

**Likely causes.** New code path, changed plan (stale statistics, parameter sniffing on generic plans),
missing index, data growth, N+1 queries from the ORM.

**Actions.**
1. Take the full text from `pg_stmt_text` (detail board) and run `EXPLAIN (ANALYZE, BUFFERS)` on a copy.
2. Check [autovacuum / analyze](autovacuum-lag.md) freshness of the involved tables.
3. Check [indexes](unused-missing-indexes.md) for seq-scan-heavy tables involved.
4. For N+1: batch the calls (`= ANY($1)`), which also collapses variants.

**Related SQL.** `sql/cluster_stmt_mask.sql`, `sql/cluster_stmt.sql`, `sql/cluster_stmt_text.sql`.
