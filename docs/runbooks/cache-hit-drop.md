# Cache hit drop / high reads

**Symptom.** Read IOPS / latency on storage grows, queries become slower under the same load.

**Where to look.** `pg-overview` → *Cache hit ratio* per database; `pg-statements` → *Top masks by shared_blks_read*.

**How to interpret.**
- Cache hit ratio = `Δblks_hit / (Δblks_hit + Δblks_read)` from `pg_db_stat` over the interval.
  OLTP: > 99 % healthy, 95–99 % warning, < 95 % critical.
- `pg_db_stat.blk_read_time` rate (needs `track_io_timing = on`) shows time spent waiting for reads.
- Masks with the highest `spread(shared_blks_read)` in `pg_stmt_mask` are the reason.
- `pg_settings_limits.shared_buffers_bytes` vs. hot data size (`pg_table_stat.total_bytes` of hot tables).

**Likely causes.** Seq scans on large tables (missing index), data growth, bulk reports / exports during load,
bloat ([autovacuum lag](autovacuum-lag.md)), too small `shared_buffers` / instance class.

**Actions.**
1. Open the top masks by reads → detail board → `EXPLAIN (ANALYZE, BUFFERS)`.
2. Add / fix indexes ([indexes](unused-missing-indexes.md)); remove bloat.
3. Move reports to a replica; schedule bulk jobs outside the test window.
4. Size `shared_buffers` / instance memory for the working set.

**Related SQL.** `sql/cluster_db_stat.sql`, `sql/cluster_stmt_mask.sql`, `sql/cluster_settings_limits.sql`.
