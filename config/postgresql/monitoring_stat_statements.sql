DROP FUNCTION IF EXISTS public.monitoring_stat_statements() ;

CREATE OR REPLACE FUNCTION public.monitoring_stat_statements()
RETURNS TABLE (
      usename               name,
      datname               name,
      query                 varchar(10000),
      query_md5             varchar(100),
      queryid               bigint,
      calls                 bigint,
      total_time            double precision,
      rows                  bigint,
      shared_blks_hit       bigint,
      shared_blks_read      bigint,
      shared_blks_dirtied   bigint,
      shared_blks_written   bigint
      )
AS $$
  SELECT
      pg_user.usename,
      pg_stat_database.datname,
      left(regexp_replace(query, '\s+', ' ', 'g'), 10000) query,
      md5(query)::uuid::varchar(100) as query_md5,
      queryid,
      calls,
      total_time,
      rows,
      shared_blks_hit,
      shared_blks_read,
      shared_blks_dirtied,
      shared_blks_written
  FROM
      pg_stat_statements
      JOIN pg_user
          ON (pg_user.usesysid = pg_stat_statements.userid)
      JOIN pg_stat_database
          ON (pg_stat_database.datid = pg_stat_statements.dbid);
$$
LANGUAGE SQL SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.monitoring_stat_statements() TO telegraf_monitoring_user;