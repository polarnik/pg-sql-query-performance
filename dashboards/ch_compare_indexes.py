"""ch-cmp-indexes: pg-cmp-indexes on ClickHouse - index composition and usage of two envs (D23)."""
from grafana_foundation_sdk.builders import dashboard

from builder.clickhouse import increase, last, series_query
from builder.compare import (
    CH_UID_INDEXES, SIDES, TOP_N_NOTE, base_dashboard, ch_changed, ch_only_in, ch_side_filters, pair_query,
    schema_links, share_pair, side_by_side,
)
from compare_indexes import COMPOSITION, FLAGS, FLAGS_NOTE, SIZE_UNITS

OBJ = ("datname", "schemaname", "relname", "indexrelname")


def pair(*filters: str) -> str:
    exprs = {"size": last("index_bytes"), **{flag: last(flag) for flag in FLAGS}}
    return pair_query("pg_index_stat", exprs, OBJ, filters)


PAIR = pair()


def _scans(side: str, *extra: str) -> str:
    return series_query("pg_index_stat", {
        "scans": increase("idx_scan"), "tup_read": increase("idx_tup_read"), "size": last("index_bytes"),
        "is_unique": last("is_unique"),
    }, ch_side_filters(side, *extra), OBJ)


def _unused(side: str, *extra: str) -> str:
    return series_query("pg_index_stat", {
        "scans_in_range": increase("idx_scan"), "scans_total": last("idx_scan"), "size": last("index_bytes"),
        **{flag: last(flag) for flag in FLAGS},
    }, ch_side_filters(side, *extra), OBJ, outer_where="scans_in_range = 0 AND is_primary = 0 AND is_unique = 0")


def _sizes(side: str, *extra: str) -> str:
    return series_query("pg_index_stat", {
        "size": last("index_bytes"), "scans_in_range": increase("idx_scan"), **{flag: last(flag) for flag in FLAGS},
    }, ch_side_filters(side, *extra), OBJ)

LINKS = schema_links(clickhouse=True)


def build():
    board = base_dashboard(
        CH_UID_INDEXES,
        "PostgreSQL (ClickHouse) / Env compare / Indexes",
        "The same Instance in Env A (left) and Env B (right): indexes of one env only, changed flags, usage and "
        "size (pg_stat_user_indexes, top 500 by size). Tables are sorted descending.",
        clickhouse=True,
    )

    board = board.with_row(dashboard.Row("Composition"))
    for side in SIDES:
        board = board.with_panel(ch_only_in(
            "", PAIR, OBJ, side, COMPOSITION, "size", h=9, links=LINKS, units=SIZE_UNITS,
            description="Indexes collected in one env only: new or missing indexes." + FLAGS_NOTE + TOP_N_NOTE,
        ))
    board = board.with_panel(ch_changed(
        "Indexes of both envs with different flags", PAIR, OBJ, COMPOSITION, FLAGS, h=7, links=LINKS, units=SIZE_UNITS,
        description="Same index name, different unique / primary / valid flag." + FLAGS_NOTE,
    ))

    board = board.with_row(dashboard.Row("Usage over the range"))
    for panel in share_pair("Indexes by scans", _scans, "scans", "scans", clickhouse=True, h=10, links=LINKS,
                            units=SIZE_UNITS,
                            description="idx_scan over the range (increase); share_pct = share of the env total: the "
                                        "load differs between envs, compare the shares."):
        board = board.with_panel(panel)
    for panel in side_by_side("Unused indexes", _unused, "size", clickhouse=True, h=9, links=LINKS, units=SIZE_UNITS,
                              description="No scans over the range, not unique / primary. Use a representative range."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Sizes"))
    for panel in side_by_side("Indexes by size", _sizes, "size", clickhouse=True, h=10, links=LINKS, units=SIZE_UNITS,
                              description="Last index size in the range." + FLAGS_NOTE):
        board = board.with_panel(panel)
    return board
