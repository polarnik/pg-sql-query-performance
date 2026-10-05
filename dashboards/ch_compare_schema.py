"""ch-cmp-schema: pg-cmp-schema on ClickHouse - one schema of the same Instance in two envs (D23)."""
from grafana_foundation_sdk.builders import dashboard

import ch_compare_indexes as idx
import ch_compare_tables as tbl
from builder.compare import (
    CH_RELNAME, CH_SCHEMA, CH_UID_SCHEMA, SIDES, TOP_N_NOTE, base_dashboard, ch_changed, ch_delta, ch_only_in,
    schema_links, schema_variables, share_pair, side_by_side,
)
from compare_indexes import COMPOSITION, FLAGS, FLAGS_NOTE, SIZE_UNITS
from compare_tables import SIZE_UNITS as TABLE_UNITS

SCOPE = (CH_SCHEMA, CH_RELNAME)
LINKS = schema_links(clickhouse=True)


def build():
    tables, indexes = tbl.pair(*SCOPE), idx.pair(*SCOPE)
    board = base_dashboard(
        CH_UID_SCHEMA,
        "PostgreSQL (ClickHouse) / Env compare / Schema",
        "One schema of the same Instance in Env A (left) and Env B (right): tables and indexes, objects of one env "
        "only and row count differences. Table regex narrows it to some tables.",
        clickhouse=True, extra_variables=schema_variables(clickhouse=True),
    )

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(ch_delta(
        "Row count differences", tables, tbl.OBJ, "rows", extra_deltas=("size",), h=9, links=LINKS,
        units={"size_a": "bytes", "size_b": "bytes", "size_delta": "bytes"},
        description="Tables of the schema in both envs, last n_live_tup and total size.",
    ))
    for side in SIDES:
        board = board.with_panel(ch_only_in(
            f"Tables only in ${{env_{side}}}", tables, tbl.OBJ, side, ("rows", "size"), "size", h=7, links=LINKS,
            units={"size": "bytes"}, description="Tables of the schema collected in one env only." + TOP_N_NOTE,
        ))
    for side in SIDES:
        board = board.with_panel(ch_only_in(
            f"Indexes only in ${{env_{side}}}", indexes, idx.OBJ, side, COMPOSITION, "size", h=7, links=LINKS,
            units=SIZE_UNITS, description="Indexes of the schema collected in one env only." + FLAGS_NOTE + TOP_N_NOTE,
        ))
    board = board.with_panel(ch_changed(
        "Indexes of both envs with different flags", indexes, idx.OBJ, COMPOSITION, FLAGS, h=6, links=LINKS,
        units=SIZE_UNITS, description="Same index name, different unique / primary / valid flag.",
    ))

    board = board.with_row(dashboard.Row("Tables"))
    for panel in side_by_side("Tables", lambda side: tbl._sizes(side, *SCOPE), "rows", clickhouse=True, h=10,
                              links=LINKS, units=TABLE_UNITS, description="Last values in the range."):
        board = board.with_panel(panel)
    for panel in share_pair("Tables by DML", lambda side: tbl._dml(side, *SCOPE), "dml", "dml", clickhouse=True, h=9,
                            links=LINKS, description="Inserted + updated + deleted rows over the range; share_pct = "
                                                     "share of the schema total of the env."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Indexes"))
    for panel in side_by_side("Indexes with their table", lambda side: idx._sizes(side, *SCOPE), "size",
                              clickhouse=True, h=10, links=LINKS, units=SIZE_UNITS,
                              description="Last index size in the range."):
        board = board.with_panel(panel)
    for panel in share_pair("Indexes by scans", lambda side: idx._scans(side, *SCOPE), "scans", "scans",
                            clickhouse=True, h=9, links=LINKS, units=SIZE_UNITS,
                            description="idx_scan over the range; share_pct = share of the schema total of the env."):
        board = board.with_panel(panel)
    return board
