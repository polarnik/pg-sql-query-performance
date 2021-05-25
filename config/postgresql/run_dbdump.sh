#!/bin/sh -x

ENV PGDATA /var/lib/postgresql/data/

set -e

#apt-get install wget unzip sudo -y
#wget -c --output-document=dbdump.zip https://edu.postgrespro.ru/demo-medium.zip
#unzip dbdump.zip -d dbdump
#mv /dbdump/demo-*.sql /dbdump/demo.sql

# https://postgrespro.ru/education/courses/QPT
#psql -t template1 --username "$POSTGRES_USER" -c "ALTER SYSTEM SET shared_preload_libraries='pg_stat_statements','pg_buffercache','pg_prewarm','auto_explain';"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/grafana_db.sql

echo "Load PostgreSQL Extensions"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

ALTER SYSTEM SET shared_preload_libraries='pg_stat_statements','auto_explain';
ALTER SYSTEM SET track_activities = 'on';
ALTER SYSTEM SET track_activity_query_size = 1000;
ALTER SYSTEM SET track_counts = 'on';
ALTER SYSTEM SET track_io_timing = 'on';
ALTER SYSTEM SET track_functions = 'all';

ALTER SYSTEM SET max_connections = 10000;
ALTER SYSTEM SET shared_buffers = '480MB';

EOSQL
echo "Load PostgreSQL Extensions ... complete"

pg_ctl -D /var/lib/postgresql/data/pgdata restart


echo "Create PostgreSQL Extensions"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

select pg_reload_conf();

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
--CREATE EXTENSION IF NOT EXISTS pg_buffercache;
--CREATE EXTENSION IF NOT EXISTS pgstattuple;
--CREATE EXTENSION IF NOT EXISTS pg_prewarm;

EOSQL

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_user.sql
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_stat_activity_count.sql
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_stat_activity_idle_in_transaction.sql
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_stat_activity_idle.sql
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_stat_activity_waiting.sql
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql.tmp/monitoring_stat_statements.sql

echo "Create Monitoring Functions ... complete"

echo "Restore Backup"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /dbdump/demo.sql
psql --username "$POSTGRES_USER" --dbname "demo" -f /sql.tmp/bookings.functions.sql

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

select * from pg_stat_statements_reset();

EOSQL


echo "Restore Backup ... complete"


