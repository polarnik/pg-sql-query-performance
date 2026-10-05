"""ch-cmp-statements: pg-cmp-statements on ClickHouse - pg_stat_statements query masks of two envs (D23).

Masks are matched by query_mask_md5 (summed over users); the text is the full mask of pg_stmt_text.
"""
from grafana_foundation_sdk.builders import dashboard

from builder.clickhouse import UID_STATEMENT_DETAIL, div, increase, series_query, table
from builder.compare import (
    CH_DATNAME, CH_INSTANCE, CH_PAIR, CH_SIDE, CH_UID_STATEMENTS, SIDES, TOP_N_NOTE, base_dashboard, ch_delta,
    ch_only_in, pair_of, share_pair,
)
from compare_statements import NOTE, UNITS, VALUES, detail_links

KEYS = ("datname", "query_mask_md5")


def _masks(env_filter: str, by_env: bool = False) -> str:
    """One row per (datname, query_mask_md5[, env]): totals over users + the mask text of pg_stmt_text."""
    env = ("env",) if by_env else ()
    keys = ", ".join(env + KEYS)
    per_user = series_query(
        "pg_stmt_mask", {"total_ms": increase("total_exec_time"), "calls": increase("calls"), "rows": increase("rows")},
        (env_filter, CH_INSTANCE, CH_DATNAME), env + ("datname", "usename", "query_mask_md5"),
    )
    sums = (f"SELECT {keys}, sum(total_ms) AS s_total_ms, sum(calls) AS s_calls, sum(rows) AS s_rows "
            f"FROM ({per_user}) GROUP BY {keys}")
    # pg_stmt_text: latest text per md5 (ReplacingMergeTree, no time filter, like ch-statement-detail)
    texts = (f"SELECT {', '.join(env + ('query_mask_md5',))}, argMax(query_mask, time) AS query_mask "
             f"FROM {table('pg_stmt_text')} WHERE {env_filter} AND {CH_INSTANCE} "
             f"GROUP BY {', '.join(env + ('query_mask_md5',))}")
    using = ", ".join(env + ("query_mask_md5",))
    return (f"SELECT {keys}, s_total_ms AS total_ms, s_calls AS calls, {div('s_total_ms', 's_calls')} AS mean_ms, "
            f"s_rows AS rows, query_mask FROM ({sums}) AS s LEFT JOIN ({texts}) AS t USING ({using})")


PAIR = pair_of(_masks(CH_PAIR, by_env=True), KEYS, VALUES)


def build():
    board = base_dashboard(
        CH_UID_STATEMENTS,
        "PostgreSQL (ClickHouse) / Env compare / Statements",
        "The same Instance in Env A (left) and Env B (right): pg_stat_statements per query mask (pg_stmt_mask, "
        "top 200), masks of one env only and mean time changes. Click query_mask_md5 for the statement detail.",
        clickhouse=True,
    )

    def links(side):
        return detail_links(side, keep="", uid=UID_STATEMENT_DETAIL)

    board = board.with_row(dashboard.Row("Top query masks"))
    for panel in share_pair("Masks by total time", lambda side: _masks(CH_SIDE[side]), "total_ms", "total_ms",
                            clickhouse=True, h=12, units=UNITS, wrap=["query_mask"], links=links,
                            description="share_pct = share of the env total exec time: the load differs between "
                                        "envs, compare the shares." + NOTE):
        board = board.with_panel(panel)
    for panel in share_pair("Masks by calls", lambda side: _masks(CH_SIDE[side]), "calls", "calls",
                            clickhouse=True, h=12, units=UNITS, wrap=["query_mask"], links=links,
                            description="share_pct = share of the env calls." + NOTE):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(ch_delta(
        "Mean time differences", PAIR, KEYS, "mean_ms", extra_deltas=("calls",), text="query_mask",
        h=12, units=UNITS, wrap=["query_mask"],
        description="Masks of both envs: mean time per call. A large delta with similar data volume is a plan "
                    "candidate (EXPLAIN on both envs)." + NOTE,
    ))
    for side in SIDES:
        board = board.with_panel(ch_only_in(
            "", PAIR, KEYS, side, VALUES, "total_ms", h=10, units=UNITS, wrap=["query_mask"], links=links(side),
            description="Masks executed in one env only (by query_mask_md5)." + TOP_N_NOTE,
        ))
    return board
