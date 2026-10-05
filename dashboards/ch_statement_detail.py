"""ch-statement-detail: pg-statement-detail on ClickHouse - one query mask -> its queryid variants -> full text (FR6).

Opened from ch-statements with &var-query_mask_md5=...&var-db_instance=...[&var-query_md5=...].
"""
from builder.clickhouse import (
    F_INSTANCE, UID_STATEMENT_DETAIL, base_dashboard, div, drill_url, f_regex, increase, last, rate_query, runbook_row,
    series_query, table_panel, timeseries_panel, var_instance, var_textbox,
)

F_MASK = f_regex("query_mask_md5")
F_QUERY = f_regex("query_md5")
MASK_SERIES = ("db_instance", "datname", "usename", "query_mask_md5")


def build():
    board = (
        base_dashboard(
            UID_STATEMENT_DETAIL,
            "PostgreSQL (ClickHouse) / Statement detail",
            "Variants and full text of one query mask. Open it from the Statements board.",
        )
        .with_variable(var_instance())
        .with_variable(var_textbox("query_mask_md5", "Mask md5"))
        .with_variable(var_textbox("query_md5", "Query md5"))
    )

    # pg_stmt_text keeps the latest text per md5 (ReplacingMergeTree, collected every 30 min): no time filter
    board = board.with_panel(table_panel(
        "Query mask",
        series_query("pg_stmt_text", {"query_mask": last("query_mask")}, (F_INSTANCE, F_MASK), ("query_mask_md5",),
                     time_filter=False),
        description="Full mask text (pg_stmt_text, collected every 30 min, latest text regardless of the time range).",
        h=8, wrap=["query_mask"],
    ))

    board = board.with_panel(timeseries_panel(
        "Calls / s",
        rate_query("pg_stmt_mask", {"calls": "calls"}, (F_INSTANCE, F_MASK), MASK_SERIES, ("db_instance", "usename"),
                   on_reset="value"),
        unit="ops", interval="5m",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call",
        rate_query("pg_stmt_mask", {"total_ms": "total_exec_time", "calls": "calls"}, (F_INSTANCE, F_MASK),
                   MASK_SERIES, ("db_instance", "usename"),
                   values={"mean_ms": div("sum({total_ms})", "sum({calls})")}, on_reset="value"),
        unit="ms", interval="5m",
        description="Execution time / calls per interval: a step up with steady calls means a plan / data regression.",
    ))

    board = board.with_panel(table_panel(
        "Variants (queryid)",
        series_query(
            "pg_stmt",
            {"total_ms": increase("total_exec_time"), "calls": increase("calls"), "rows": increase("rows"),
             "blks_read": increase("shared_blks_read"), "blks_hit": increase("shared_blks_hit"),
             "temp_blks_written": increase("temp_blks_written"), "query": last("query_short")},
            (F_INSTANCE, F_MASK),
            ("db_instance", "datname", "usename", "queryid", "query_md5", "query_mask_md5", "toplevel"),
            extra={"mean_ms": div("total_ms", "calls")},
        ),
        description="Statements behind the mask. Click query_md5 to filter the full text below.",
        h=10, sort_by="total_ms", units={"total_ms": "ms", "mean_ms": "ms"},
        links={"query_md5": ("Show full text", drill_url(
            UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5",
            db_instance="db_instance"))},
    ))

    board = board.with_panel(table_panel(
        "Full text",
        series_query("pg_stmt_text", {"queryid": last("queryid"), "query": last("query")},
                     (F_INSTANCE, F_MASK, F_QUERY), ("query_md5",), time_filter=False),
        description="Full statement text (≤ 10000 chars). Use it for EXPLAIN (ANALYZE, BUFFERS) on a copy.",
        h=12, wrap=["query"],
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    return board
