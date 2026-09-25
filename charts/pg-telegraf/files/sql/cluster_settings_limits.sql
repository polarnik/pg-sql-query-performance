-- measurement: pg_settings_limits | scope: cluster (maintenance DB) | interval: 5m
-- tags: db_instance (global)
SELECT
    current_setting('max_connections')::int                         AS max_connections,
    current_setting('superuser_reserved_connections')::int          AS superuser_reserved,
    current_setting('reserved_connections')::int                    AS reserved,
    current_setting('max_connections')::int
        - current_setting('superuser_reserved_connections')::int
        - current_setting('reserved_connections')::int              AS effective_limit,
    (SELECT count(*) FROM pg_stat_activity
      WHERE backend_type = 'client backend')                        AS client_backends,
    pg_size_bytes(current_setting('shared_buffers'))                AS shared_buffers_bytes,
    pg_size_bytes(current_setting('work_mem'))                      AS work_mem_bytes,
    pg_size_bytes(current_setting('maintenance_work_mem'))          AS maintenance_work_mem_bytes,
    (SELECT setting::bigint FROM pg_settings
      WHERE name = 'statement_timeout')                             AS statement_timeout_ms,
    (SELECT setting::bigint FROM pg_settings
      WHERE name = 'idle_in_transaction_session_timeout')           AS idle_in_transaction_session_timeout_ms,
    (SELECT setting::bigint FROM pg_settings
      WHERE name = 'idle_session_timeout')                          AS idle_session_timeout_ms,
    coalesce(current_setting('pg_stat_statements.max', true), '0')::int AS pg_stat_statements_max,
    pg_size_bytes(current_setting('track_activity_query_size'))      AS track_activity_query_size_bytes,
    extract(epoch FROM pg_postmaster_start_time())::bigint          AS postmaster_start_epoch,
    current_setting('server_version_num')::int                      AS server_version_num;
