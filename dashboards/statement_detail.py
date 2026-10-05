"""pg-statement-detail: one query mask -> its queryid variants -> full text (FR6).

Opened from pg-statements with &var-query_mask_md5=...&var-env=...&var-db_instance=...[&var-query_md5=...][&var-queryid=...].
Key hierarchy: query_mask_md5 -> query_md5 (several texts per mask) -> queryid (several per text).
"""
from builder.common import (
    F_ENV, F_INSTANCE, UID_STATEMENT_DETAIL, base_dashboard, var_rp, drill_url, runbook_row, table_panel,
    timeseries_panel, var_env, var_instance, var_textbox, where,
)

F_MASK = 'query_mask_md5 =~ /^$query_mask_md5$/'
F_QUERY = 'query_md5 =~ /^$query_md5$/'
F_QUERYID = '"queryid"::tag =~ /^$queryid$/'
STMT_FILTERS = (F_ENV, F_INSTANCE, F_MASK, F_QUERY, F_QUERYID)


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
            "PostgreSQL / Statement detail",
            "Variants and full text of one query mask. Open it from the Statements board.",
        )
        .with_variable(var_rp())
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_textbox("query_mask_md5", "Mask md5"))
        .with_variable(var_textbox("query_md5", "Query md5"))
        .with_variable(var_textbox("queryid", "Query id"))
    )

    board = board.with_panel(table_panel(
        "Query mask",
        f"""SELECT last("query_mask") AS "query_mask" FROM "$rp"."pg_stmt_text"
            WHERE {where(F_ENV, F_INSTANCE, F_MASK)} GROUP BY "env", "query_mask_md5" """,
        description="Full mask text (pg_stmt_text, collected every 10 min).",
        h=8, wrap=["query_mask"],
    ))

    board = board.with_panel(timeseries_panel(
        "Calls / s",
        f"""SELECT non_negative_derivative(last("calls"), 1s) FROM "$rp"."pg_stmt_mask"
            WHERE {where(F_ENV, F_INSTANCE, F_MASK)} GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)""",
        unit="ops", interval="1m",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call",
        f"""SELECT "t" / "c" FROM (
                SELECT non_negative_difference(last("total_exec_time")) AS "t",
                       non_negative_difference(last("calls")) AS "c"
                FROM "$rp"."pg_stmt_mask" WHERE {where(F_ENV, F_INSTANCE, F_MASK)}
                GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)
            ) GROUP BY "env", "db_instance", "usename" """,
        unit="ms", interval="1m",
        description="Execution time / calls per interval: a step up with steady calls means a plan / data regression.",
    ))
    board = board.with_panel(timeseries_panel(
        "Rows per call",
        f"""SELECT "r" / "c" AS "rows" FROM (
                SELECT non_negative_difference(last("rows")) AS "r",
                       non_negative_difference(last("calls")) AS "c"
                FROM "$rp"."pg_stmt_mask" WHERE {where(F_ENV, F_INSTANCE, F_MASK)}
                GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)
            ) GROUP BY "env", "db_instance", "usename" """,
        interval="1m",
        description="Rows returned / affected per call: growth means the result set (data or filter) changes.",
    ))
    board = board.with_panel(timeseries_panel(
        "Shared blocks per call",
        f"""SELECT "h" / "c" AS "blks_hit", "r" / "c" AS "blks_read" FROM (
                SELECT non_negative_difference(last("shared_blks_hit")) AS "h",
                       non_negative_difference(last("shared_blks_read")) AS "r",
                       non_negative_difference(last("calls")) AS "c"
                FROM "$rp"."pg_stmt_mask" WHERE {where(F_ENV, F_INSTANCE, F_MASK)}
                GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)
            ) GROUP BY "env", "db_instance", "usename" """,
        interval="1m",
        description="Buffer hits / reads per call (8 KB blocks): growth with steady rows per call means "
                    "more pages scanned for the same result (plan change, bloat).",
    ))
    board = board.with_panel(timeseries_panel(
        "Calls / s by queryid",
        f"""SELECT sum("d") AS "calls" FROM (
                SELECT non_negative_derivative(last("calls"), 1s) AS "d" FROM "$rp"."pg_stmt"
                WHERE {where(*STMT_FILTERS)} GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "env", "db_instance", "usename", "queryid" fill(none)""",
        unit="ops", interval="1m",
        description="pg_stmt (top-N) of the variants selected by query_md5 / queryid (all variants of the mask by default).",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call by queryid",
        f"""SELECT sum("t") / sum("c") AS "mean_ms" FROM (
                SELECT non_negative_difference(last("total_exec_time")) AS "t",
                       non_negative_difference(last("calls")) AS "c"
                FROM "$rp"."pg_stmt" WHERE {where(*STMT_FILTERS)}
                GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "env", "db_instance", "usename", "queryid" fill(none)""",
        unit="ms", interval="1m",
        description="Execution time / calls per interval of the selected variants: shows which queryid regressed.",
    ))

    board = board.with_panel(table_panel(
        "Variants (queryid)",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("shared_blks_hit") AS "blks_hit",
                   spread("temp_blks_written") AS "temp_blks_written", last("query_short") AS "query"
            FROM "$rp"."pg_stmt" WHERE {where(*STMT_FILTERS)}
            GROUP BY "env", "db_instance", "datname", "usename", "query_mask_md5", "query_md5", "queryid", "toplevel" """,
        description="Statements behind the mask (narrowed by the query_md5 / queryid variables). "
                    "Click query_md5 / queryid to filter the board, query_mask_md5 to show the whole mask again.",
        h=10, sort_by="total_ms", units={"total_ms": "ms", "mean_ms": "ms"}, links=LINKS,
    ))

    board = board.with_panel(table_panel(
        "Full text",
        f"""SELECT last("query") AS "query" FROM "$rp"."pg_stmt_text"
            WHERE {where(*STMT_FILTERS)} GROUP BY "env", "db_instance", "query_mask_md5", "query_md5", "queryid" """,
        description="Full statement text (≤ 10000 chars), one row per query_md5 + queryid. "
                    "Use it for EXPLAIN (ANALYZE, BUFFERS) on a copy.",
        h=12, wrap=["query"], links=LINKS,
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    return board
