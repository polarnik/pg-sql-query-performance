"""pg-statements: totals by datname / db_instance / usename (Breakdown, click to filter the board),
query masks and statements over the time range, click an md5 to drill down (FR5, FR6, D14)."""
from grafana_foundation_sdk.builders import dashboard

from builder.common import (
    F_DATNAME, F_ENV, F_INSTANCE, F_USENAME, UID_STATEMENT_DETAIL, UID_STATEMENTS, base_dashboard, var_rp, drill_url,
    field_filter_url, increase_query, last_sum_query, runbook_row, series_filter_url, stat_panel, table_panel,
    timeseries_panel, var_datname, var_env, var_instance, var_usename, where,
)

UNITS = {"total_ms": "ms", "mean_ms": "ms", "blks_read": "short", "temp_blks_written": "short"}
TOTALS_UNITS = {"total_ms": "ms", "mean_ms": "ms", "blk_read_ms": "ms", "hit_ratio": "percent",
                "calls": "short", "rows": "short", "blks_read": "short", "blks_hit": "short",
                "temp_blks_written": "short", "statements": "short"}

# pg_stmt_totals: alias -> cumulative counter
TOTALS = {"total_ms": "total_exec_time", "calls": "calls", "rows": "rows", "blks_read": "shared_blks_read",
          "blks_hit": "shared_blks_hit", "temp_blks_written": "temp_blks_written",
          "blk_read_ms": "shared_blk_read_time"}
MEAN = 'sum("total_ms") / sum("calls")'
HIT = '100 * sum("blks_hit") / (sum("blks_hit") + sum("blks_read"))'
ALL_FILTERS = (F_ENV, F_INSTANCE, F_DATNAME, F_USENAME)

TOTALS_NOTE = ("Sum over ALL pg_stat_statements entries (pg_stmt_totals), increase over the range. "
               "Click datname / db_instance / usename to filter the whole board.")
TOP_N_NOTE = (" Top-N subset: totals here are ≤ Breakdown totals. "
              "Click datname / db_instance / usename to filter the whole board.")
FILTER_LINKS = {tag: (f"Filter board by {tag}", field_filter_url(UID_STATEMENTS, tag))
                for tag in ("env", "db_instance", "datname", "usename")}


def _stat(title: str, fields: dict[str, str], unit: str, extra: dict[str, str] | None = None, desc: str = ""):
    return stat_panel(title, increase_query(fields, "pg_stmt_totals", ALL_FILTERS, extra=extra), unit=unit, w=4,
                      description=desc or TOTALS_NOTE)


def _breakdown_table(title: str, group_by: tuple[str, ...]):
    group_by = ("env",) + group_by
    links = {tag: (f"Filter board by {tag}", field_filter_url(UID_STATEMENTS, tag)) for tag in group_by}
    return table_panel(
        title,
        [increase_query(TOTALS, "pg_stmt_totals", ALL_FILTERS, group_by=group_by,
                        extra={"mean_ms": MEAN, "hit_ratio": HIT}),
         last_sum_query("statements", "pg_stmt_totals", ALL_FILTERS, group_by=group_by)],
        description=TOTALS_NOTE + " statements = pg_stat_statements entries at the end of the range.",
        h=8, sort_by="total_ms", units=TOTALS_UNITS, links=links,
    )


def _rate_by(title: str, field: str, tag: str, unit: str, stacked: bool = True, w: int = 12):
    return timeseries_panel(
        title,
        f"""SELECT sum("d") FROM (
                SELECT non_negative_derivative(last("{field}"), 1s) AS "d" FROM "$rp"."pg_stmt_totals"
                WHERE {where(*ALL_FILTERS)} GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "env", "{tag}" fill(none)""",
        unit=unit, interval="1m", stacked=stacked, alias=f"$tag_{tag} ($tag_env)", w=w,
        links=[(f"Filter board by {tag}", series_filter_url(UID_STATEMENTS, "env", tag))],
        description=f"All statements (pg_stmt_totals) per {tag}. Click a series to filter the board.",
    )


def build():
    board = (
        base_dashboard(
            UID_STATEMENTS,
            "PostgreSQL / Statements",
            "pg_stat_statements totals by datname / db_instance / usename (pg_stmt_totals, all entries) and "
            "top-N by query mask and by queryid. Click datname / db_instance / usename to filter the board.",
        )
        .with_variable(var_rp())
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_datname())
        .with_variable(var_usename())
    )

    # ---- Breakdown: complete totals by datname / datname+db_instance / datname+usename (D14)
    board = board.with_row(dashboard.Row("Breakdown: datname / db_instance / usename"))
    board = board.with_panel(_stat("Total exec time", {"total_ms": "total_exec_time"}, "ms"))
    board = board.with_panel(_stat("Calls", {"calls": "calls"}, "short"))
    board = board.with_panel(_stat("Mean time", {"total_ms": "total_exec_time", "calls": "calls"}, "ms",
                                   extra={"mean_ms": MEAN}))
    board = board.with_panel(_stat("Rows", {"rows": "rows"}, "short"))
    board = board.with_panel(_stat("Cache hit %", {"blks_hit": "shared_blks_hit", "blks_read": "shared_blks_read"},
                                   "percent", extra={"hit_ratio": HIT}))
    board = board.with_panel(stat_panel(
        "Statements (entries)", last_sum_query("statements", "pg_stmt_totals", ALL_FILTERS), w=4,
        description="pg_stat_statements entries at the end of the range (compare with pg_stat_statements.max).",
    ))
    board = board.with_panel(_breakdown_table("Totals by datname", ("datname",)))
    board = board.with_panel(_breakdown_table("Totals by datname + db_instance", ("datname", "db_instance")))
    board = board.with_panel(_breakdown_table("Totals by datname + usename", ("datname", "usename")))
    board = board.with_panel(_rate_by("Exec time / s by datname", "total_exec_time", "datname", "ms"))
    board = board.with_panel(_rate_by("Exec time / s by usename", "total_exec_time", "usename", "ms"))

    # ---- Top-N: masks and statements
    board = board.with_row(dashboard.Row("Top query masks / statements"))
    board = board.with_panel(_rate_by(
        "Execution time / s (all statements)", "total_exec_time", "db_instance", "ms", stacked=False))
    board = board.with_panel(_rate_by("Calls / s (all statements)", "calls", "db_instance", "ops", stacked=False))

    board = board.with_panel(table_panel(
        "Top query masks",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("shared_blks_hit") AS "blks_hit",
                   spread("temp_blks_written") AS "temp_blks_written", last("variants") AS "variants",
                   last("query_mask_short") AS "query_mask"
            FROM "$rp"."pg_stmt_mask" WHERE {where(*ALL_FILTERS)}
            GROUP BY "env", "db_instance", "datname", "usename", "query_mask_md5" """,
        description="One row per mask (IN-lists / VALUES collapsed). Click query_mask_md5 for variants and full text."
                    + TOP_N_NOTE,
        h=14, sort_by="total_ms", units=UNITS,
        links={**FILTER_LINKS, "query_mask_md5": ("Statement detail", drill_url(
            UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", env="env", db_instance="db_instance"))},
    ))
    board = board.with_panel(table_panel(
        "Top statements (queryid)",
        f"""SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls",
                   spread("total_exec_time") / spread("calls") AS "mean_ms", spread("rows") AS "rows",
                   spread("shared_blks_read") AS "blks_read", spread("temp_blks_written") AS "temp_blks_written",
                   last("query_short") AS "query"
            FROM "$rp"."pg_stmt" WHERE {where(*ALL_FILTERS)}
            GROUP BY "env", "db_instance", "datname", "usename", "query_mask_md5", "query_md5", "queryid", "toplevel" """,
        description="Top-N by cumulative total_exec_time ∪ top-N by calls. Click query_mask_md5 / query_md5 / queryid "
                    "for the statement detail narrowed to that key."
                    + TOP_N_NOTE,
        h=12, sort_by="total_ms", units=UNITS,
        links={
            **FILTER_LINKS,
            "query_md5": ("Statement detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5",
                env="env", db_instance="db_instance")),
            "queryid": ("Statement detail (queryid)", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5", queryid="queryid",
                env="env", db_instance="db_instance")),
            "query_mask_md5": ("Mask detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", env="env", db_instance="db_instance")),
        },
    ))

    board = board.with_panel(table_panel(
        "Statements health",
        f"""SELECT last("entries") AS "entries", last("max_entries") AS "max_entries",
                   last("dealloc") AS "dealloc", spread("dealloc") AS "dealloc_in_range",
                   last("stats_reset_epoch") * 1000 AS "stats_reset"
            FROM "$rp"."pg_stmt_info" WHERE {where(F_ENV, F_INSTANCE)} GROUP BY "env", "db_instance" """,
        description="dealloc_in_range > 0: entries were evicted, raise pg_stat_statements.max. "
                    "stats_reset inside the range: counters were reset.",
        h=6, units={"stats_reset": "dateTimeAsIso"}, thresholds={"dealloc_in_range": (1, 100)},
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    board = board.with_row(runbook_row("pg_stat_statements reset / dealloc", "stat-statements-reset"))
    return board
