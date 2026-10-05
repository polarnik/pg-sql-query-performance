"""ch-statements: pg-statements on ClickHouse - totals by datname / db_instance / usename (Breakdown, click to
filter the board), query masks and statements over the time range, click an md5 to drill down (FR5, FR6, D14)."""
from grafana_foundation_sdk.builders import dashboard

from builder.clickhouse import (
    F_DATNAME, F_ENV, F_INSTANCE, F_USENAME, UID_STATEMENT_DETAIL, UID_STATEMENTS, base_dashboard, div, drill_url,
    field_filter_url, increase, last, rate_query, runbook_row, series_filter_url, series_query, stat_panel,
    table_panel, timeseries_panel, var_datname, var_env, var_instance, var_usename,
)
from statements import TOP_N_NOTE, TOTALS_UNITS, UNITS

ALL_FILTERS = (F_ENV, F_INSTANCE, F_DATNAME, F_USENAME)
SERIES = ("env", "db_instance", "datname", "usename")

# pg_stmt_totals: alias -> cumulative counter (sums over all entries: dealloc drops are ignored, D14b)
TOTALS = {"total_ms": "total_exec_time", "calls": "calls", "rows": "rows", "blks_read": "shared_blks_read",
          "blks_hit": "shared_blks_hit", "temp_blks_written": "temp_blks_written",
          "blk_read_ms": "shared_blk_read_time"}
MEAN = div("total_ms", "calls")
HIT = div("blks_hit", "(blks_hit + blks_read)", "100 * ")

TOTALS_NOTE = ("Sum over ALL pg_stat_statements entries (pg_stmt_totals), increase over the range. "
               "Click datname / db_instance / usename to filter the whole board.")
FILTER_LINKS = {tag: (f"Filter board by {tag}", field_filter_url(UID_STATEMENTS, tag))
                for tag in ("env", "db_instance", "datname", "usename")}

# per-entry counters of pg_stmt_mask / pg_stmt (spread() in pg-*): alias -> counter
ENTRY = {"total_ms": "total_exec_time", "calls": "calls", "rows": "rows", "blks_read": "shared_blks_read",
         "blks_hit": "shared_blks_hit", "temp_blks_written": "temp_blks_written"}


def _totals(fields: dict[str, str], group_by: tuple[str, ...] = (), extra: dict[str, str] | None = None,
            statements: bool = False) -> str:
    exprs = {alias: increase(column, on_reset="ignore") for alias, column in fields.items()}
    if statements:
        exprs["statements"] = last("statements")
    return series_query("pg_stmt_totals", exprs, ALL_FILTERS, SERIES, group_by=group_by, extra=extra)


def _stat(title: str, fields: dict[str, str], unit: str, extra: dict[str, str] | None = None):
    query = _totals(fields, extra=extra)
    if extra:  # show the derived value only
        query = f"SELECT {', '.join(extra)} FROM ({query})"
    return stat_panel(title, query, unit=unit, w=4, description=TOTALS_NOTE)


def _breakdown_table(title: str, group_by: tuple[str, ...]):
    group_by = ("env",) + group_by
    links = {tag: (f"Filter board by {tag}", field_filter_url(UID_STATEMENTS, tag)) for tag in group_by}
    return table_panel(
        title,
        _totals(TOTALS, group_by=group_by, extra={"mean_ms": MEAN, "hit_ratio": HIT}, statements=True),
        description=TOTALS_NOTE + " statements = pg_stat_statements entries at the end of the range.",
        h=8, sort_by="total_ms", units=TOTALS_UNITS, links=links,
    )


def _rate_by(title: str, field: str, tag: str, unit: str, stacked: bool = True, w: int = 12):
    return timeseries_panel(
        title,
        rate_query("pg_stmt_totals", {field: field}, ALL_FILTERS, SERIES, ("env", tag)),
        unit=unit, interval="5m", stacked=stacked, w=w,
        links=[(f"Filter board by {tag}", series_filter_url(UID_STATEMENTS, "env", tag))],
        description=f"All statements (pg_stmt_totals) per {tag}. Click a series to filter the board.",
    )


def build():
    board = (
        base_dashboard(
            UID_STATEMENTS,
            "PostgreSQL (ClickHouse) / Statements",
            "pg_stat_statements totals by datname / db_instance / usename (pg_stmt_totals, all entries) and "
            "top-N by query mask and by queryid. Click datname / db_instance / usename to filter the board.",
        )
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
        "Statements (entries)",
        series_query("pg_stmt_totals", {"statements": last("statements")}, ALL_FILTERS, SERIES, group_by=()), w=4,
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
        series_query(
            "pg_stmt_mask",
            {**{alias: increase(column) for alias, column in ENTRY.items()},
             "variants": last("variants"), "query_mask": last("query_mask_short")},
            ALL_FILTERS, SERIES + ("query_mask_md5",),
            extra={"mean_ms": MEAN},
        ),
        description="One row per mask (IN-lists / VALUES collapsed). Click query_mask_md5 for variants and full text."
                    + TOP_N_NOTE,
        h=14, sort_by="total_ms", units=UNITS,
        links={**FILTER_LINKS, "query_mask_md5": ("Statement detail", drill_url(
            UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", env="env", db_instance="db_instance"))},
    ))
    board = board.with_panel(table_panel(
        "Top statements (queryid)",
        series_query(
            "pg_stmt",
            {**{alias: increase(column) for alias, column in ENTRY.items() if alias != "blks_hit"},
             "query": last("query_short")},
            ALL_FILTERS, SERIES + ("queryid", "query_md5", "query_mask_md5", "toplevel"),
            extra={"mean_ms": MEAN},
        ),
        description="Top-N by cumulative total_exec_time ∪ top-N by calls. Click query_md5 for the full text."
                    + TOP_N_NOTE,
        h=12, sort_by="total_ms", units=UNITS,
        links={
            **FILTER_LINKS,
            "query_md5": ("Statement detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", query_md5="query_md5",
                env="env", db_instance="db_instance")),
            "query_mask_md5": ("Mask detail", drill_url(
                UID_STATEMENT_DETAIL, query_mask_md5="query_mask_md5", env="env", db_instance="db_instance")),
        },
    ))

    board = board.with_panel(table_panel(
        "Statements health",
        series_query(
            "pg_stmt_info",
            {"entries": last("entries"), "max_entries": last("max_entries"), "dealloc": last("dealloc"),
             "dealloc_in_range": increase("dealloc"), "stats_reset": f"{last('stats_reset_epoch')} * 1000"},
            (F_ENV, F_INSTANCE), ("env", "db_instance"),
        ),
        description="dealloc_in_range > 0: entries were evicted, raise pg_stat_statements.max. "
                    "stats_reset inside the range: counters were reset.",
        h=6, units={"stats_reset": "dateTimeAsIso"}, thresholds={"dealloc_in_range": (1, 100)},
    ))

    board = board.with_row(runbook_row("Slow query regression", "slow-query-regression"))
    board = board.with_row(runbook_row("pg_stat_statements reset / dealloc", "stat-statements-reset"))
    return board
