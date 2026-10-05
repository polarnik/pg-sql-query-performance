"""pg-cmp-statements: the same Instance in two envs - pg_stat_statements query masks side by side (D23).

Masks are matched by query_mask_md5 (summed over users: the roles may differ between envs).
"""
from grafana_foundation_sdk.builders import dashboard

from builder.common import KEEP_RP, UID_STATEMENT_DETAIL, src, where
from builder.compare import (
    SIDES, TOP_N_NOTE, UID_STATEMENTS, base_dashboard, influx_delta, influx_only_in, share_pair, side_filters,
)

UNITS = {"total_ms": "ms", "mean_ms": "ms", "mean_ms_a": "ms", "mean_ms_b": "ms", "delta": "ms",
         "total_ms_a": "ms", "total_ms_b": "ms"}
VALUES = ("total_ms", "calls", "mean_ms", "rows", "query_mask")
NOTE = " Per query mask (IN-lists / VALUES collapsed), summed over users, increase over the range."


def detail_links(side: str, keep: str = KEEP_RP, uid: str = UID_STATEMENT_DETAIL) -> dict[str, tuple[str, str]]:
    """query_mask_md5 -> statement detail of the env of the side."""
    url = (f"/d/{uid}?${{__url_time_range}}{keep}&var-env=${{env_{side}}}&var-db_instance=${{db_instance}}"
           "&var-query_mask_md5=${__data.fields.query_mask_md5}")
    return {"query_mask_md5": ("Statement detail", url)}


def _masks(side: str, suffix: str = "", by_env: bool = False) -> str:
    """One row per (datname, query_mask_md5) of one env; column names + suffix (e.g. '_a')."""
    env = '"env", ' if by_env else ""
    inner = (f'SELECT spread("total_exec_time") AS "total_ms", spread("calls") AS "calls", spread("rows") AS "rows", '
             f'last("query_mask_short") AS "query_mask" FROM {src("pg_stmt_mask")} '
             f'WHERE {where(*side_filters(side))} GROUP BY {env}"datname", "usename", "query_mask_md5"')
    return (f'SELECT sum("total_ms") AS "total_ms{suffix}", sum("calls") AS "calls{suffix}", '
            f'sum("total_ms") / sum("calls") AS "mean_ms{suffix}", sum("rows") AS "rows{suffix}", '
            f'last("query_mask") AS "query_mask{suffix}" FROM ({inner}) GROUP BY {env}"datname", "query_mask_md5"')


def build():
    board = base_dashboard(
        UID_STATEMENTS,
        "PostgreSQL / Env compare / Statements",
        "The same Instance in Env A (left) and Env B (right): pg_stat_statements per query mask (pg_stmt_mask, "
        "top 200), masks of one env only and mean time changes. Click query_mask_md5 for the statement detail.",
    )

    board = board.with_row(dashboard.Row("Top query masks"))
    for panel in share_pair("Masks by total time", lambda side: _masks(side, by_env=True), "total_ms", "total_ms",
                            h=12, units=UNITS, wrap=["query_mask"], links=detail_links,
                            description="share_pct = share of the env total exec time: the load differs between "
                                        "envs, compare the shares." + NOTE):
        board = board.with_panel(panel)
    for panel in share_pair("Masks by calls", lambda side: _masks(side, by_env=True), "calls", "calls",
                            h=12, units=UNITS, wrap=["query_mask"], links=detail_links,
                            description="share_pct = share of the env calls." + NOTE):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(influx_delta(
        "Mean time differences", lambda side: _masks(side, f"_{side}"), "mean_ms", extra_deltas=("calls",),
        text="query_mask", h=12, units=UNITS, wrap=["query_mask"],
        description="Masks of both envs: mean time per call. A large delta with similar data volume is a plan "
                    "candidate (EXPLAIN on both envs)." + NOTE,
    ))
    for side in SIDES:
        board = board.with_panel(influx_only_in(
            "", lambda s: _masks(s, f"_{s}"), side, VALUES, "total_ms", h=10, units=UNITS, wrap=["query_mask"],
            links=detail_links(side),
            description="Masks executed in one env only (by query_mask_md5)." + TOP_N_NOTE,
        ))
    return board
