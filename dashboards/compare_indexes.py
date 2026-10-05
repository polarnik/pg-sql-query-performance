"""pg-cmp-indexes: the same Instance in two envs - index composition (only in A / B, changed flags) and usage (D23)."""
from grafana_foundation_sdk.builders import dashboard

from builder.common import src, where
from builder.compare import (
    SIDES, TOP_N_NOTE, UID_INDEXES, base_dashboard, influx_changed, influx_only_in, schema_links, share_pair,
    side_by_side, side_filters,
)

OBJ = '"datname", "schemaname", "relname", "indexrelname"'
INDEX = src("pg_index_stat")
FLAGS = ("is_unique", "is_primary", "is_valid")
COMPOSITION = ("size",) + FLAGS
SIZE_UNITS = {"size": "bytes", "size_a": "bytes", "size_b": "bytes"}
FLAGS_NOTE = " is_valid = 0: failed CREATE INDEX CONCURRENTLY."


def _composition(side: str, *extra: str) -> str:
    flags = ", ".join(f'last("{flag}") AS "{flag}_{side}"' for flag in FLAGS)
    return (f'SELECT last("index_bytes") AS "size_{side}", {flags} FROM {INDEX} '
            f'WHERE {where(*side_filters(side, *extra))} GROUP BY {OBJ}')


def _scans(side: str, *extra: str) -> str:
    return (f'SELECT spread("idx_scan") AS "scans", spread("idx_tup_read") AS "tup_read", '
            f'last("index_bytes") AS "size", last("is_unique") AS "is_unique" FROM {INDEX} '
            f'WHERE {where(*side_filters(side, *extra))} GROUP BY "env", {OBJ}')


def _unused(side: str, *extra: str) -> str:
    return (f'SELECT * FROM (SELECT spread("idx_scan") AS "scans_in_range", last("idx_scan") AS "scans_total", '
            f'last("index_bytes") AS "size", last("is_unique") AS "is_unique", last("is_primary") AS "is_primary", '
            f'last("is_valid") AS "is_valid" FROM {INDEX} WHERE {where(*side_filters(side, *extra))} GROUP BY {OBJ}) '
            f'WHERE "scans_in_range" = 0 AND "is_primary" = 0 AND "is_unique" = 0 GROUP BY *')


def _sizes(side: str, *extra: str) -> str:
    return (f'SELECT last("index_bytes") AS "size", spread("idx_scan") AS "scans_in_range", '
            f'last("is_unique") AS "is_unique", last("is_primary") AS "is_primary", last("is_valid") AS "is_valid" '
            f'FROM {INDEX} WHERE {where(*side_filters(side, *extra))} GROUP BY {OBJ}')

LINKS = schema_links()


def build():
    board = base_dashboard(
        UID_INDEXES,
        "PostgreSQL / Env compare / Indexes",
        "The same Instance in Env A (left) and Env B (right): indexes of one env only, changed flags, usage and "
        "size (pg_stat_user_indexes, top 500 by size). Tables are sorted descending.",
    )

    board = board.with_row(dashboard.Row("Composition"))
    for side in SIDES:
        board = board.with_panel(influx_only_in(
            "", _composition, side, COMPOSITION, "size", h=9, links=LINKS, units=SIZE_UNITS,
            description="Indexes collected in one env only: new or missing indexes." + FLAGS_NOTE + TOP_N_NOTE,
        ))
    board = board.with_panel(influx_changed(
        "Indexes of both envs with different flags", _composition, "size", FLAGS, h=7, links=LINKS, units=SIZE_UNITS,
        description="Same index name, different unique / primary / valid flag." + FLAGS_NOTE,
    ))

    board = board.with_row(dashboard.Row("Usage over the range"))
    for panel in share_pair("Indexes by scans", _scans, "scans", "scans", h=10, links=LINKS, units=SIZE_UNITS,
                            description="idx_scan over the range (spread); share_pct = share of the env total: the "
                                        "load differs between envs, compare the shares."):
        board = board.with_panel(panel)
    for panel in side_by_side("Unused indexes", _unused, "size", h=9, links=LINKS, units=SIZE_UNITS,
                              description="No scans over the range, not unique / primary. Use a representative range."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Sizes"))
    for panel in side_by_side("Indexes by size", _sizes, "size", h=10, links=LINKS, units=SIZE_UNITS,
                              description="Last index size in the range." + FLAGS_NOTE):
        board = board.with_panel(panel)
    return board
