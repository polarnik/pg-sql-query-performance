"""ch-indexes: pg-indexes on ClickHouse - unused / large indexes, seq-scan-heavy tables, dead tuples, vacuum (FR7)."""
from builder.clickhouse import (
    F_DATNAME, F_ENV, F_INSTANCE, UID_INDEXES, base_dashboard, increase, last, runbook_row, series_query,
    table_panel, var_datname, var_env, var_instance,
)

OBJ = ("env", "db_instance", "datname", "schemaname", "relname")
INDEX = OBJ + ("indexrelname",)
FILTERS = (F_ENV, F_INSTANCE, F_DATNAME)


def build():
    board = (
        base_dashboard(
            UID_INDEXES,
            "PostgreSQL (ClickHouse) / Indexes and tables",
            "Per-database object statistics (pg_stat_user_tables / pg_stat_user_indexes, top by size).",
        )
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    board = board.with_panel(table_panel(
        "Unused indexes",
        series_query(
            "pg_index_stat",
            {"scans_in_range": increase("idx_scan"), "scans_total": last("idx_scan"), "size": last("index_bytes"),
             "is_unique": last("is_unique"), "is_primary": last("is_primary"), "is_valid": last("is_valid"),
             "last_scan": f"{last('last_idx_scan_epoch')} * 1000"},
            FILTERS, INDEX,
            outer_where="scans_in_range = 0 AND is_primary = 0 AND is_unique = 0",
        ),
        description="No scans over the range, not unique / primary. Use a representative range (full test or ≥ 7 days). "
                    "last_scan = 1970 means never scanned since stats reset.",
        h=10, sort_by="size", units={"size": "bytes", "last_scan": "dateTimeAsIso"},
    ))
    board = board.with_panel(table_panel(
        "Indexes by size",
        series_query(
            "pg_index_stat",
            {"size": last("index_bytes"), "scans_in_range": increase("idx_scan"),
             "tup_read_in_range": increase("idx_tup_read"), "is_unique": last("is_unique"),
             "is_valid": last("is_valid")},
            FILTERS, INDEX,
        ),
        description="is_valid = 0: failed CREATE INDEX CONCURRENTLY, drop and re-create.",
        h=10, sort_by="size", units={"size": "bytes"},
    ))
    board = board.with_panel(table_panel(
        "Seq-scan-heavy tables",
        series_query(
            "pg_table_stat",
            {"seq_scans": increase("seq_scan"), "seq_tup_read": increase("seq_tup_read"),
             "idx_scans": increase("idx_scan"), "live_tup": last("n_live_tup"), "total_size": last("total_bytes"),
             "last_seq_scan": f"{last('last_seq_scan_epoch')} * 1000"},
            FILTERS, OBJ,
        ),
        description="Large tables with many rows read by seq scans are missing-index candidates.",
        h=10, sort_by="seq_tup_read", units={"total_size": "bytes", "last_seq_scan": "dateTimeAsIso"},
    ))
    board = board.with_panel(table_panel(
        "Dead tuples and vacuum",
        series_query(
            "pg_table_stat",
            {"dead_tup": last("n_dead_tup"), "dead_pct": last("dead_tup_pct"),
             "mod_since_analyze": last("n_mod_since_analyze"),
             "upd_in_range": increase("n_tup_upd"), "del_in_range": increase("n_tup_del"),
             "autovacuums_in_range": increase("autovacuum_count"),
             "last_vacuum": f"{last('last_any_vacuum_epoch')} * 1000",
             "last_analyze": f"{last('last_any_analyze_epoch')} * 1000"},
            FILTERS, OBJ,
            extra={"upd_del_in_range": "upd_in_range + del_in_range"},
        ),
        description="dead_pct > 10 %: warning, > 20 %: critical. Old last_vacuum with many updates: autovacuum lags.",
        h=10, sort_by="dead_pct",
        units={"dead_pct": "percent", "last_vacuum": "dateTimeAsIso", "last_analyze": "dateTimeAsIso"},
        thresholds={"dead_pct": (10, 20)},
    ))

    board = board.with_row(runbook_row("Unused / missing indexes", "unused-missing-indexes"))
    board = board.with_row(runbook_row("Autovacuum lag / dead tuples", "autovacuum-lag"))
    return board
