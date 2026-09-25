# pg_stat_statements reset / dealloc

**Symptom.** Statement tables show negative or sudden drops, masks disappear, totals look too small.

**Where to look.** `pg-statements` → *Statements health* row (dealloc, entries / max, last reset).

**How to interpret.**
- `pg_stmt_info.stats_reset_epoch` changed inside the range → counters were reset; `spread()` across the reset is wrong,
  use a range that starts after the reset.
- `pg_settings_limits.postmaster_start_epoch` changed → restart / failover, all counters restart from 0.
- `spread(pg_stmt_info.dealloc)` > 0 → entries were evicted because `entries` reached `max_entries`
  (`pg_stat_statements.max`); rare statements are lost and totals are underestimated.
- `pg_stmt.stats_since_epoch` newer than the range start → that statement entry was (re)created inside the range.

**Likely causes.** Someone called `pg_stat_statements_reset()`, instance restart / failover,
too many distinct statements (unparameterized SQL, variable IN-lists, temp tables) with a small `pg_stat_statements.max`.

**Actions.**
1. Choose a time range that does not cross the reset / restart.
2. If `dealloc` grows: raise `pg_stat_statements.max` (e.g. 10000) in the parameter group; parameterize SQL;
   use `= ANY($1)` instead of variable IN-lists.
3. Agree on a reset policy for perf tests (reset only at test start, record the time in the test report).

**Related SQL.** `sql/cluster_stmt_info.sql`, `sql/cluster_settings_limits.sql`, `sql/cluster_stmt.sql`.
