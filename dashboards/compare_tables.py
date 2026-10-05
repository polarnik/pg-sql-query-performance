"""pg-cmp-tables: the same Instance in two envs - table row counts, sizes and activity side by side (D23)."""
from grafana_foundation_sdk.builders import dashboard

from builder.common import src, where
from builder.compare import (
    SIDES, TOP_N_NOTE, UID_TABLES, base_dashboard, influx_delta, influx_only_in, schema_links, share_pair, side_by_side,
    side_filters,
)

OBJ = '"datname", "schemaname", "relname"'
TABLE = src("pg_table_stat")
SIZE_UNITS = {"total_size": "bytes", "table_size": "bytes", "index_size": "bytes"}


def _rows(side: str, *extra: str) -> str:
    return (f'SELECT last("n_live_tup") AS "rows_{side}", last("total_bytes") AS "size_{side}" FROM {TABLE} '
            f'WHERE {where(*side_filters(side, *extra))} GROUP BY {OBJ}')


def _sizes(side: str, *extra: str) -> str:
    return (f'SELECT last("n_live_tup") AS "rows", last("total_bytes") AS "total_size", '
            f'last("table_bytes") AS "table_size", last("indexes_bytes") AS "index_size", '
            f'last("n_dead_tup") AS "dead_tup" FROM {TABLE} WHERE {where(*side_filters(side, *extra))} GROUP BY {OBJ}')


def _scans(side: str, *extra: str) -> str:
    return (f'SELECT spread("seq_tup_read") AS "seq_tup_read", spread("seq_scan") AS "seq_scans", '
            f'spread("idx_scan") AS "idx_scans", last("n_live_tup") AS "rows" FROM {TABLE} '
            f'WHERE {where(*side_filters(side, *extra))} GROUP BY "env", {OBJ}')


def _dml(side: str, *extra: str) -> str:
    return (f'SELECT spread("n_tup_ins") + spread("n_tup_upd") + spread("n_tup_del") AS "dml", '
            f'spread("n_tup_ins") AS "ins", spread("n_tup_upd") AS "upd", spread("n_tup_del") AS "del", '
            f'spread("n_tup_hot_upd") AS "hot_upd" FROM {TABLE} WHERE {where(*side_filters(side, *extra))} '
            f'GROUP BY "env", {OBJ}')

LINKS = schema_links()


def build():
    board = base_dashboard(
        UID_TABLES,
        "PostgreSQL / Env compare / Tables",
        "The same Instance in Env A (left) and Env B (right): row counts, sizes, scans and DML per table "
        "(pg_stat_user_tables, top 300 by size). Tables are sorted descending.",
    )

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(influx_delta(
        "Row count differences", _rows, "rows", extra_deltas=("size",),
        description="Tables of both envs, last n_live_tup (estimate, updated by ANALYZE) and total size.",
        h=10, links=LINKS, units={"size_a": "bytes", "size_b": "bytes", "size_delta": "bytes"},
    ))
    for side in SIDES:
        board = board.with_panel(influx_only_in(
            "", _rows, side, ("rows", "size"), "size", description="Tables collected in one env only." + TOP_N_NOTE,
            h=8, links=LINKS, units={"size": "bytes"},
        ))

    board = board.with_row(dashboard.Row("Rows and sizes"))
    for panel in side_by_side("Tables by rows", _sizes, "rows", h=12, links=LINKS, units=SIZE_UNITS,
                              description="Last values in the range: n_live_tup, total / heap / index size, "
                                          "dead tuples."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Activity over the range"))
    for panel in share_pair("Tables by seq_tup_read", _scans, "seq_tup_read", "seq_tup_read", h=10, links=LINKS,
                            description="Rows read by seq scans over the range (spread); share_pct = share of the "
                                        "env total: the load differs between envs, compare the shares."):
        board = board.with_panel(panel)
    for panel in share_pair("Tables by DML", _dml, "dml", "dml", h=10, links=LINKS,
                            description="Inserted + updated + deleted rows over the range; share_pct = share of the "
                                        "env total."):
        board = board.with_panel(panel)
    return board
