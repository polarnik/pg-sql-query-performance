"""ch-statement-detail: pg-statement-detail on ClickHouse - one query mask -> its queryid variants -> full text (FR6).

Opened from ch-statements with &var-query_mask_md5=...&var-env=...&var-db_instance=...[&var-query_md5=...][&var-queryid=...].
Key hierarchy: query_mask_md5 -> query_md5 (several texts per mask) -> queryid (several per text).
"""
from builder.clickhouse import (
    F_ENV, F_INSTANCE, UID_STATEMENT_DETAIL, base_dashboard, div, drill_url, f_regex, increase, last, rate_query,
    runbook_row, series_query, table_panel, timeseries_panel, var_env, var_instance, var_textbox,
)

F_MASK = f_regex("query_mask_md5")
F_QUERY = f_regex("query_md5")
F_QUERYID = f_regex("queryid")
MASK_SERIES = ("env", "db_instance", "datname", "usename", "query_mask_md5")
STMT_SERIES = MASK_SERIES + ("query_md5", "queryid", "toplevel")
STMT_FILTERS = (F_ENV, F_INSTANCE, F_MASK, F_QUERY, F_QUERYID)
STMT_BY = ("env", "db_instance", "usename", "queryid")


def _detail_url(*keys: str) -> str:
    """This board narrowed to the row values of `keys` (the omitted md5 / queryid variables fall back to .*)."""
    return drill_url(UID_STATEMENT_DETAIL, **{key: key for key in keys}, env="env", db_instance="db_instance")


LINKS = {
    "query_mask_md5": ("Whole mask", _detail_url("query_mask_md5")),
    "query_md5": ("Filter by query_md5", _detail_url("query_mask_md5", "query_md5")),
    "queryid": ("Filter by queryid", _detail_url("query_mask_md5", "query_md5", "queryid")),
}


def build():
    board = (
        base_dashboard(
            UID_STATEMENT_DETAIL,
            "PostgreSQL (ClickHouse) / Statement detail",
            "Variants and full text of one query mask. Open it from the Statements board.",
        )
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_textbox("query_mask_md5", "Mask md5"))
        .with_variable(var_textbox("query_md5", "Query md5"))
        .with_variable(var_textbox("queryid", "Query id"))
    )

    # pg_stmt_text keeps the latest text per md5 + queryid (ReplacingMergeTree, collected every 10 min): no time filter
    board = board.with_panel(table_panel(
        "Query mask",
        series_query("pg_stmt_text", {"query_mask": last("query_mask")}, (F_ENV, F_INSTANCE, F_MASK),
                     ("env", "query_mask_md5"), time_filter=False),
        description="Full mask text (pg_stmt_text, collected every 10 min, latest text regardless of the time range).",
        h=8, wrap=["query_mask"],
    ))

    board = board.with_panel(timeseries_panel(
        "Calls / s",
        rate_query("pg_stmt_mask", {"calls": "calls"}, (F_ENV, F_INSTANCE, F_MASK), MASK_SERIES,
                   ("env", "db_instance", "usename"), on_reset="value"),
        unit="ops", interval="1m",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call",
        rate_query("pg_stmt_mask", {"total_ms": "total_exec_time", "calls": "calls"}, (F_ENV, F_INSTANCE, F_MASK),
                   MASK_SERIES, ("env", "db_instance", "usename"),
                   values={"mean_ms": div("sum({total_ms})", "sum({calls})")}, on_reset="value"),
        unit="ms", interval="1m",
        description="Execution time / calls per interval: a step up with steady calls means a plan / data regression.",
    ))
    board = board.with_panel(timeseries_panel(
        "Rows per call",
        rate_query("pg_stmt_mask", {"rows": "rows", "calls": "calls"}, (F_ENV, F_INSTANCE, F_MASK),
                   MASK_SERIES, ("env", "db_instance", "usename"),
                   values={"rows": div("sum({rows})", "sum({calls})")}, on_reset="value"),
        interval="1m",
        description="Rows returned / affected per call: growth means the result set (data or filter) changes.",
    ))
    board = board.with_panel(timeseries_panel(
        "Shared blocks per call",
        rate_query("pg_stmt_mask", {"hit": "shared_blks_hit", "read": "shared_blks_read", "calls": "calls"},
                   (F_ENV, F_INSTANCE, F_MASK), MASK_SERIES, ("env", "db_instance", "usename"),
                   values={"blks_hit": div("sum({hit})", "sum({calls})"),
                           "blks_read": div("sum({read})", "sum({calls})")}, on_reset="value"),
        interval="1m",
        description="Buffer hits / reads per call (8 KB blocks): growth with steady rows per call means "
                    "more pages scanned for the same result (plan change, bloat).",
    ))
    board = board.with_panel(timeseries_panel(
        "Calls / s by queryid",
        rate_query("pg_stmt", {"calls": "calls"}, STMT_FILTERS, STMT_SERIES, STMT_BY, on_reset="value"),
        unit="ops", interval="1m",
        description="pg_stmt (top-N) of the variants selected by query_md5 / queryid (all variants of the mask by default).",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call by queryid",
        rate_query("pg_stmt", {"total_ms": "total_exec_time", "calls": "calls"}, STMT_FILTERS, STMT_SERIES, STMT_BY,
                   values={"mean_ms": div("sum({total_ms})", "sum({calls})")}, on_reset="value"),
        unit="ms", interval="1m",
        description="Execution time / calls per interval of the selected variants: shows which queryid regressed.",
    ))

    board = board.with_panel(table_panel(
        "Variants (queryid)",
        series_query(
            "pg_stmt",
            {"total_ms": increase("total_exec_time"), "calls": increase("calls"), "rows": increase("rows"),
             "blks_read": increase("shared_blks_read"), "blks_hit": increase("shared_blks_hit"),
             "temp_blks_written": increase("temp_blks_written"), "query": last("query_short")},
            STMT_FILTERS, STMT_SERIES,
            extra={"mean_ms": div("total_ms", "calls")},
        ),
        description="Statements behind the mask (narrowed by the query_md5 / queryid variables). "
                    "Click query_md5 / queryid to filter the board, query_mask_md5 to show the whole mask again.",
        h=10, sort_by="total_ms", units={"total_ms": "ms", "mean_ms": "ms"}, links=LINKS,
    ))

    board = board.with_panel(table_panel(
        "Full text",
        series_query("pg_stmt_text", {"query": last("query")}, STMT_FILTERS,
                     ("env", "db_instance", "query_mask_md5", "query_md5", "queryid"), time_filter=False),
        description="Full statement text (≤ 10000 chars), one row per query_md5 + queryid. "
                    "Use it for EXPLAIN (ANALYZE, BUFFERS) on a copy.",
        h=12, wrap=["query"], links=LINKS,
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    return board
