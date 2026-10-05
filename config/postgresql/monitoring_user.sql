-- Monitoring user for Telegraf: no DB objects, only the built-in pg_monitor role
-- (includes pg_read_all_settings, pg_read_all_stats, pg_stat_scan_tables).
-- On RDS run the same as the master user; pg_stat_statements must be enabled by the DBA.
CREATE USER telegraf_monitoring_user WITH ENCRYPTED PASSWORD 'pass';
GRANT pg_monitor TO telegraf_monitoring_user;
