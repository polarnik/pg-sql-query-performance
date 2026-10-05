-- measurement: pg_db_stat | scope: cluster | interval: 1m
-- tags: datname
-- All counters are cumulative since stats_reset -> use non_negative_derivative / spread() in Grafana.
SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched,
    tup_inserted,
    tup_updated,
    tup_deleted,
    conflicts,
    temp_files,
    temp_bytes,
    deadlocks,
    coalesce(checksum_failures, 0)                                  AS checksum_failures,
    blk_read_time,
    blk_write_time,
    session_time,
    active_time,
    idle_in_transaction_time,
    sessions,
    sessions_abandoned,
    sessions_fatal,
    sessions_killed,
    coalesce(extract(epoch FROM stats_reset), 0)::bigint            AS stats_reset_epoch
FROM pg_stat_database
WHERE datname IS NOT NULL
  AND datname NOT IN ('rdsadmin', 'template0', 'template1');
