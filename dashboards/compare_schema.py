"""pg-cmp-schema: the same Instance in two envs - one schema (optionally a table regex): its tables and indexes (D23).

Opened from the schemaname / relname cells of pg-cmp-tables / pg-cmp-indexes.
"""
from grafana_foundation_sdk.builders import dashboard

import compare_indexes as idx
import compare_tables as tbl
from builder.compare import (
    F_RELNAME, F_SCHEMA, SIDES, TOP_N_NOTE, UID_SCHEMA, base_dashboard, influx_changed, influx_delta, influx_only_in,
    schema_links, schema_variables, share_pair, side_by_side,
)

SCOPE = (F_SCHEMA, F_RELNAME)
LINKS = schema_links()


def build():
    board = base_dashboard(
        UID_SCHEMA,
        "PostgreSQL / Env compare / Schema",
        "One schema of the same Instance in Env A (left) and Env B (right): tables and indexes, objects of one env "
        "only and row count differences. Table regex narrows it to some tables.",
        extra_variables=schema_variables(),
    )

    board = board.with_row(dashboard.Row("Differences"))
    board = board.with_panel(influx_delta(
        "Row count differences", lambda side: tbl._rows(side, *SCOPE), "rows", extra_deltas=("size",), h=9,
        links=LINKS, units={"size_a": "bytes", "size_b": "bytes", "size_delta": "bytes"},
        description="Tables of the schema in both envs, last n_live_tup and total size.",
    ))
    for side in SIDES:
        board = board.with_panel(influx_only_in(
            f"Tables only in ${{env_{side}}}", lambda s: tbl._rows(s, *SCOPE), side, ("rows", "size"), "size", h=7,
            links=LINKS, units={"size": "bytes"},
            description="Tables of the schema collected in one env only." + TOP_N_NOTE,
        ))
    for side in SIDES:
        board = board.with_panel(influx_only_in(
            f"Indexes only in ${{env_{side}}}", lambda s: idx._composition(s, *SCOPE), side, idx.COMPOSITION, "size",
            h=7, links=LINKS, units=idx.SIZE_UNITS,
            description="Indexes of the schema collected in one env only." + idx.FLAGS_NOTE + TOP_N_NOTE,
        ))
    board = board.with_panel(influx_changed(
        "Indexes of both envs with different flags", lambda s: idx._composition(s, *SCOPE), "size", idx.FLAGS, h=6,
        links=LINKS, units=idx.SIZE_UNITS, description="Same index name, different unique / primary / valid flag.",
    ))

    board = board.with_row(dashboard.Row("Tables"))
    for panel in side_by_side("Tables", lambda side: tbl._sizes(side, *SCOPE), "rows", h=10, links=LINKS,
                              units=tbl.SIZE_UNITS, description="Last values in the range."):
        board = board.with_panel(panel)
    for panel in share_pair("Tables by DML", lambda side: tbl._dml(side, *SCOPE), "dml", "dml", h=9, links=LINKS,
                            description="Inserted + updated + deleted rows over the range; share_pct = share of the "
                                        "schema total of the env."):
        board = board.with_panel(panel)

    board = board.with_row(dashboard.Row("Indexes"))
    for panel in side_by_side("Indexes with their table", lambda side: idx._sizes(side, *SCOPE), "size", h=10,
                              links=LINKS, units=idx.SIZE_UNITS, description="Last index size in the range."):
        board = board.with_panel(panel)
    for panel in share_pair("Indexes by scans", lambda side: idx._scans(side, *SCOPE), "scans", "scans", h=9,
                            links=LINKS, units=idx.SIZE_UNITS,
                            description="idx_scan over the range; share_pct = share of the schema total of the env."):
        board = board.with_panel(panel)
    return board
