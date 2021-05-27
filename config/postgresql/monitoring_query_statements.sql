DROP FUNCTION IF EXISTS  monitoring_query_statements() ;

CREATE OR REPLACE FUNCTION monitoring_query_statements()
RETURNS TABLE (
      query                 varchar(10000),
      query_md5             varchar(100),
      queryid               bigint
      )
AS $$
  SELECT
      left(regexp_replace(query, '\s+', ' ', 'g'), 10000) query,
      md5(query)::uuid::varchar(100) as query_md5,
      queryid
  FROM
      pg_stat_statements
$$
LANGUAGE SQL SECURITY DEFINER;