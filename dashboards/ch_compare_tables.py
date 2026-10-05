"""ch-cmp-tables: pg-cmp-tables on ClickHouse - table row counts, sizes and activity of two envs (D23)."""
from grafana_foundation_sdk.builders import dashboard

from builder.clickhouse import increase, last, series_query
from builder.compare import (
    CH_UID_TABLES, SIDES, TOP_N_NOTE, base_dashboard, ch_delta, ch_only_in, ch_side_filters, pair_query, schema_links,
    share_pair, side_by_side,
)
from compare_tables import SIZE_UNITS

OBJ = ("datname", "schemaname", "relname")


def pair(*filters: str) -> str:
    return pair_query("pg_table_stat", {"rows": last("n_live_tup"), "size": last("total_bytes")}, OBJ, filters)


PAIR = pair()


def _sizes(side: str, *extra: str) -> str:
    return series_query("pg_table_stat", {
        "rows": last("n_live_tup"), "total_size": last("total_bytes"), "table_size": last("table_bytes"),
        "index_size": last("indexes_bytes"), "dead_tup": last("n_dead_tup"),
    }, ch_side_filters(side, *extra), OBJ)


def _scans(side: str, *extra: str) -> str:
    return series_query("pg_table_stat", {
        "seq_tup_read": increase("seq_tup_read"), "seq_scans": increase("seq_scan"), "idx_scans": increase("idx_scan"),
        "rows": last("n_live_tup"),
    }, ch_side_filters(side, *extra), OBJ)


def _dml(side: str, *extra: str) -> str:
    return series_query("pg_table_stat", {
        "ins": increase("n_tup_ins"), "upd": increase("n_tup_upd"), "del": increase("n_tup_del"),
        "hot_upd": increase("n_tup_hot_upd"),
    }, ch_side_filters(side, *extra), OBJ, extra={"dml": "ins + upd + del"})

LINKS = schema_links(clickhouse=True)


def build():
    board = base_dashboard(
        CH_UID_TABLES,
        "PostgreSQL (ClickHouse) / Env compare / Tables",
        "The same Instance in Env A (left) and Env B (right): row counts, sizes, scans and DML per table "
        "(pg_stat_user_tables, top 300 by size). Tables are sorted descending.",
        clickhouse=True,
    )

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(ch_delta(
        "Row count differences", PAIR, OBJ, "rows", extra_deltas=("size",),
        description="Tables of both envs, last n_live_tup (estimate, updated by ANALYZE) and total size.",
        h=10, links=LINKS, units={"size_a": "bytes", "size_b": "bytes", "size_delta": "bytes"},
    ))
    for side in SIDES:
        board = board.with_panel(ch_only_in(
            "", PAIR, OBJ, side, ("rows", "size"), "size", description="Tables collected in one env only." + TOP_N_NOTE,
            h=8, links=LINKS, units={"size": "bytes"},
        ))

    board = board.with_row(dashboard.Row("Rows and sizes"))
    for panel in side_by_side("Tables by rows", _sizes, "rows", clickhouse=True, h=12, links=LINKS, units=SIZE_UNITS,
                              description="Last values in the range: n_live_tup, total / heap / index size, "
                                          "dead tuples."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Activity over the range"))
    for panel in share_pair("Tables by seq_tup_read", _scans, "seq_tup_read", "seq_tup_read", clickhouse=True, h=10,
                            links=LINKS,
                            description="Rows read by seq scans over the range (increase); share_pct = share of the "
                                        "env total: the load differs between envs, compare the shares."):
        board = board.with_panel(panel)
    for panel in share_pair("Tables by DML", _dml, "dml", "dml", clickhouse=True, h=10, links=LINKS,
                            description="Inserted + updated + deleted rows over the range; share_pct = share of the "
                                        "env total."):
        board = board.with_panel(panel)
    return board
