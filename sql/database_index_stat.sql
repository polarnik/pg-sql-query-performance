-- measurement: pg_index_stat | scope: per app database (connect to each DB) | interval: 10m
-- tags: datname, schemaname, relname, indexrelname
-- Top 500 indexes by size. Unused index = idx_scan does not grow over the range (spread = 0)
-- and it is not unique/primary (those enforce constraints).
SELECT
    current_database()                                              AS datname,
    i.schemaname,
    i.relname,
    i.indexrelname,
    x.indisunique::int                                              AS is_unique,
    x.indisprimary::int                                             AS is_primary,
    x.indisvalid::int                                               AS is_valid,
    i.idx_scan,
    i.idx_tup_read,
    i.idx_tup_fetch,
    coalesce(extract(epoch FROM i.last_idx_scan), 0)::bigint        AS last_idx_scan_epoch,
    pg_relation_size(i.indexrelid)                                  AS index_bytes
FROM pg_stat_user_indexes i
    JOIN pg_index x ON x.indexrelid = i.indexrelid
ORDER BY pg_relation_size(i.indexrelid) DESC
LIMIT 500;
