# Idle-in-transaction leaks

**Symptom.** Growing lock waits, table bloat, autovacuum cannot clean rows, connections stuck in `idle in transaction`.

**Where to look.** `pg-connections` → *Grouped connections* table filtered by `state =~ /idle in transaction/`,
column *Oldest xact age*.

**How to interpret.**
- `pg_activity_grouped.cnt` for `state = 'idle in transaction'` > 0 for more than a few seconds is suspicious.
- `max_xact_age_s` > 60 s: warning; > 300 s: critical (holds back vacuum horizon and may hold locks).
- `pg_db_stat.idle_in_transaction_time` rate shows total time spent idle inside transactions.
- `pg_settings_limits.idle_in_transaction_session_timeout_ms = 0` means no server-side protection.

**Likely causes.**
- Application opens a transaction, then does remote calls / user think-time before commit.
- Missing `commit` / `rollback` in error paths; ORM `autocommit=false` with long-lived sessions.
- `idle in transaction (aborted)`: an error was ignored and the session was not rolled back.

**Actions.**
1. Identify `application_name` + `usename` with the largest `max_xact_age_s`.
2. Fix transaction scope in the code; move external calls outside transactions.
3. Set `idle_in_transaction_session_timeout` (e.g. 60 s) for the application role.
4. Emergency: `SELECT pg_terminate_backend(pid)` for the offending sessions (DBA).

**Related SQL.** `sql/cluster_activity_grouped.sql`, `sql/cluster_db_stat.sql`, `sql/cluster_settings_limits.sql`.
