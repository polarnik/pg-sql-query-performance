#!/bin/sh -x

ENV PGDATA /var/lib/postgresql/data/

set -e

#apt-get install wget unzip sudo -y
#wget -c --output-document=dbdump.zip https://edu.postgrespro.ru/demo-medium.zip
#unzip dbdump.zip -d dbdump
#mv /dbdump/demo-medium-*.sql /dbdump/demo.sql

# https://postgrespro.ru/education/courses/QPT
#psql -t template1 --username "$POSTGRES_USER" -c "ALTER SYSTEM SET shared_preload_libraries='pg_stat_statements','pg_buffercache','pg_prewarm','auto_explain';"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

ALTER SYSTEM SET shared_preload_libraries='pg_stat_statements','auto_explain';
ALTER SYSTEM SET track_activities = 'on';
ALTER SYSTEM SET track_activity_query_size = 1000;
ALTER SYSTEM SET track_counts = 'on';
ALTER SYSTEM SET track_io_timing = 'on';
ALTER SYSTEM SET track_functions = 'all';

EOSQL


pg_ctl -D /var/lib/postgresql/data/pgdata restart


psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

select pg_reload_conf();

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
--CREATE EXTENSION IF NOT EXISTS pg_buffercache;
--CREATE EXTENSION IF NOT EXISTS pgstattuple;
--CREATE EXTENSION IF NOT EXISTS pg_prewarm;

EOSQL



#psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /dbdump/demo.sql