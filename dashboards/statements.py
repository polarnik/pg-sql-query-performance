"""pg-statements: query masks and statements over the time range, click an md5 to drill down (FR5, FR6)."""
from builder.common import (
    F_DATNAME, F_INSTANCE, UID_STATEMENT_DETAIL, UID_STATEMENTS, base_dashboard, drill_url, runbook_row,
    table_panel, timeseries_panel, var_datname, var_instance, where,
)

UNITS = {"total_ms": "ms", "mean_ms": "ms", "blks_read": "short", "temp_blks_written": "short"}


def build():
    board = (
        base_dashboard(
            UID_STATEMENTS,
            "PostgreSQL / Statements",
            "pg_stat_statements aggregated by query mask and by queryid. Counters use spread() over the range.",
        )
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    board = board.with_panel(timeseries_panel(
        "Execution time / s (all statements)",
        f"""SELECT sum("d") FROM (
                SELECT non_negative_derivative(last("total_exec_time"), 1s) AS "d" FROM "pg_stmt_mask"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "db_instance" fill(none)""",
        unit="ms", interval="5m",
        description="Milliseconds of execution per second (≈ busy backends × 1000).",
    ))
    board = board.with_panel(timeseries_panel(
        "Calls / s (all statements)",
        f"""SELECT sum("d") FROM (
                SELECT non_negative_derivative(last("calls"), 1s) AS "d" FROM "pg_stmt_mask"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "db_instance" fill(none)""",
        unit="ops", interval="5m",
    ))

    board = board.with_panel(table_panel(
        "Top query masks",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("shared_blks_hit") AS "blks_hit",
                   spread("temp_blks_written") AS "temp_blks_written", last("variants") AS "variants",
                   last("query_mask_short") AS "query_mask"
            FROM "pg_stmt_mask" WHERE {where(F_INSTANCE, F_DATNAME)}
            GROUP BY "db_instance", "datname", "usename", "query_mask_md5" """,
        description="One row per mask (IN-lists / VALUES collapsed). Click query_mask_md5 for variants and full text.",
        h=14, sort_by="total_ms", units=UNITS,
        links={"query_mask_md5": ("Statement detail", drill_url(
            UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", db_instance="db_instance"))},
    ))
    board = board.with_panel(table_panel(
        "Top statements (queryid)",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("temp_blks_written") AS "temp_blks_written",
                   last("query_short") AS "query"
            FROM "pg_stmt" WHERE {where(F_INSTANCE, F_DATNAME)}
            GROUP BY "db_instance", "datname", "usename", "queryid", "query_md5", "query_mask_md5", "toplevel" """,
        description="Top-N by cumulative total_exec_time ∪ top-N by calls. Click query_md5 for the full text.",
        h=12, sort_by="total_ms", units=UNITS,
        links={
            "query_md5": ("Statement detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5",
                db_instance="db_instance")),
            "query_mask_md5": ("Mask detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", db_instance="db_instance")),
        },
    ))

    board = board.with_panel(table_panel(
        "Statements health",
        f"""SELECT last("entries") AS "entries", last("max_entries") AS "max_entries",
                   last("dealloc") AS "dealloc", spread("dealloc") AS "dealloc_in_range",
                   last("stats_reset_epoch") * 1000 AS "stats_reset"
            FROM "pg_stmt_info" WHERE {where(F_INSTANCE)} GROUP BY "db_instance" """,
        description="dealloc_in_range > 0: entries were evicted, raise pg_stat_statements.max. "
                    "stats_reset inside the range: counters were reset.",
        h=6, units={"stats_reset": "dateTimeAsIso"}, thresholds={"dealloc_in_range": (1, 100)},
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    board = board.with_row(runbook_row("pg_stat_statements reset / dealloc", "stat-statements-reset"))
    return board
