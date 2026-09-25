"""pg-indexes: unused / large indexes, seq-scan-heavy tables, dead tuples and vacuum (FR7)."""
from builder.common import (
    F_DATNAME, F_INSTANCE, UID_INDEXES, base_dashboard, runbook_row, table_panel, var_datname, var_instance,
    where,
)

OBJ = '"db_instance", "datname", "schemaname", "relname"'


def build():
    board = (
        base_dashboard(
            UID_INDEXES,
            "PostgreSQL / Indexes and tables",
            "Per-database object statistics (pg_stat_user_tables / pg_stat_user_indexes, top by size).",
        )
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    board = board.with_panel(table_panel(
        "Unused indexes",
        f"""SELECT * FROM (
                SELECT spread("idx_scan") AS "scans_in_range", last("idx_scan") AS "scans_total",
                       last("index_bytes") AS "size", last("is_unique") AS "is_unique",
                       last("is_primary") AS "is_primary", last("is_valid") AS "is_valid",
                       last("last_idx_scan_epoch") * 1000 AS "last_scan"
                FROM "pg_index_stat" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY {OBJ}, "indexrelname"
            ) WHERE "scans_in_range" = 0 AND "is_primary" = 0 AND "is_unique" = 0 GROUP BY *""",
        description="No scans over the range, not unique / primary. Use a representative range (full test or ≥ 7 days). "
                    "last_scan = 1970 means never scanned since stats reset.",
        h=10, sort_by="size", units={"size": "bytes", "last_scan": "dateTimeAsIso"},
    ))
    board = board.with_panel(table_panel(
        "Indexes by size",
        f"""SELECT last("index_bytes") AS "size", spread("idx_scan") AS "scans_in_range",
                   spread("idx_tup_read") AS "tup_read_in_range", last("is_unique") AS "is_unique",
                   last("is_valid") AS "is_valid"
            FROM "pg_index_stat" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY {OBJ}, "indexrelname" """,
        description="is_valid = 0: failed CREATE INDEX CONCURRENTLY, drop and re-create.",
        h=10, sort_by="size", units={"size": "bytes"},
    ))
    board = board.with_panel(table_panel(
        "Seq-scan-heavy tables",
        f"""SELECT spread("seq_scan") AS "seq_scans", spread("seq_tup_read") AS "seq_tup_read",
                   spread("idx_scan") AS "idx_scans", last("n_live_tup") AS "live_tup",
                   last("total_bytes") AS "total_size", last("last_seq_scan_epoch") * 1000 AS "last_seq_scan"
            FROM "pg_table_stat" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY {OBJ}""",
        description="Large tables with many rows read by seq scans are missing-index candidates.",
        h=10, sort_by="seq_tup_read", units={"total_size": "bytes", "last_seq_scan": "dateTimeAsIso"},
    ))
    board = board.with_panel(table_panel(
        "Dead tuples and vacuum",
        f"""SELECT last("n_dead_tup") AS "dead_tup", last("dead_tup_pct") AS "dead_pct",
                   last("n_mod_since_analyze") AS "mod_since_analyze",
                   spread("n_tup_upd") + spread("n_tup_del") AS "upd_del_in_range",
                   spread("autovacuum_count") AS "autovacuums_in_range",
                   last("last_any_vacuum_epoch") * 1000 AS "last_vacuum",
                   last("last_any_analyze_epoch") * 1000 AS "last_analyze"
            FROM "pg_table_stat" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY {OBJ}""",
        description="dead_pct > 10 %: warning, > 20 %: critical. Old last_vacuum with many updates: autovacuum lags.",
        h=10, sort_by="dead_pct",
        units={"dead_pct": "percent", "last_vacuum": "dateTimeAsIso", "last_analyze": "dateTimeAsIso"},
        thresholds={"dead_pct": (10, 20)},
    ))

    board = board.with_row(runbook_row("Unused / missing indexes", "unused-missing-indexes"))
    board = board.with_row(runbook_row("Autovacuum lag / dead tuples", "autovacuum-lag"))
    return board
