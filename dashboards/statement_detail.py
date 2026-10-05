"""pg-statement-detail: one query mask -> its queryid variants -> full text (FR6).

Opened from pg-statements with &var-query_mask_md5=...&var-env=...&var-db_instance=...[&var-query_md5=...].
"""
from builder.common import (
    F_ENV, F_INSTANCE, UID_STATEMENT_DETAIL, base_dashboard, var_rp, drill_url, runbook_row, table_panel,
    timeseries_panel, var_env, var_instance, var_textbox, where,
)

F_MASK = 'query_mask_md5 =~ /^$query_mask_md5$/'
F_QUERY = 'query_md5 =~ /^$query_md5$/'


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
    )

    board = board.with_panel(table_panel(
        "Query mask",
        f"""SELECT last("query_mask") AS "query_mask" FROM "$rp"."pg_stmt_text"
            WHERE {where(F_ENV, F_INSTANCE, F_MASK)} GROUP BY "env", "query_mask_md5" """,
        description="Full mask text (pg_stmt_text, collected every 30 min).",
        h=8, wrap=["query_mask"],
    ))

    board = board.with_panel(timeseries_panel(
        "Calls / s",
        f"""SELECT non_negative_derivative(last("calls"), 1s) FROM "$rp"."pg_stmt_mask"
            WHERE {where(F_ENV, F_INSTANCE, F_MASK)} GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)""",
        unit="ops", interval="5m",
    ))
    board = board.with_panel(timeseries_panel(
        "Mean time per call",
        f"""SELECT "t" / "c" FROM (
                SELECT non_negative_difference(last("total_exec_time")) AS "t",
                       non_negative_difference(last("calls")) AS "c"
                FROM "$rp"."pg_stmt_mask" WHERE {where(F_ENV, F_INSTANCE, F_MASK)}
                GROUP BY time($__interval), "env", "db_instance", "usename" fill(none)
            ) GROUP BY "env", "db_instance", "usename" """,
        unit="ms", interval="5m",
        description="Execution time / calls per interval: a step up with steady calls means a plan / data regression.",
    ))

    board = board.with_panel(table_panel(
        "Variants (queryid)",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("shared_blks_hit") AS "blks_hit",
                   spread("temp_blks_written") AS "temp_blks_written", last("query_short") AS "query"
            FROM "$rp"."pg_stmt" WHERE {where(F_ENV, F_INSTANCE, F_MASK)}
            GROUP BY "env", "db_instance", "datname", "usename", "queryid", "query_md5", "query_mask_md5", "toplevel" """,
        description="Statements behind the mask. Click query_md5 to filter the full text below.",
        h=10, sort_by="total_ms", units={"total_ms": "ms", "mean_ms": "ms"},
        links={"query_md5": ("Show full text", drill_url(
            UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5",
            env="env", db_instance="db_instance"))},
    ))

    board = board.with_panel(table_panel(
        "Full text",
        f"""SELECT last("queryid") AS "queryid", last("query") AS "query" FROM "$rp"."pg_stmt_text"
            WHERE {where(F_ENV, F_INSTANCE, F_MASK, F_QUERY)} GROUP BY "env", "query_md5" """,
        description="Full statement text (≤ 10000 chars). Use it for EXPLAIN (ANALYZE, BUFFERS) on a copy.",
        h=12, wrap=["query"],
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    return board
