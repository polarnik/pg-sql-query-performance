"""pg-connections: connection limits (server / database / role) and grouped connection usage."""
from builder.common import (
    F_DATNAME, F_INSTANCE, UID_CONNECTIONS, base_dashboard, runbook_row, table_panel,
    timeseries_panel, var_datname, var_instance, where,
)

USAGE_THRESHOLDS = (70, 90)


def build():
    board = (
        base_dashboard(
            UID_CONNECTIONS,
            "PostgreSQL / Connections",
            "Connection limits and usage grouped by state, application and user. See docs/runbooks.",
        )
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    # ---- limits (FR3)
    board = board.with_panel(table_panel(
        "Server limit usage",
        f"""SELECT last("client_backends") AS "used", last("effective_limit") AS "limit",
                   last("client_backends") / last("effective_limit") * 100 AS "usage_pct",
                   last("max_connections") AS "max_connections",
                   last("superuser_reserved") AS "superuser_reserved", last("reserved") AS "reserved"
            FROM "pg_settings_limits" WHERE {where(F_INSTANCE)} GROUP BY "db_instance" """,
        description="effective limit = max_connections - superuser_reserved_connections - reserved_connections "
                    "(5 min sample).",
        w=24, h=6, sort_by="usage_pct",
        units={"usage_pct": "percent"}, thresholds={"usage_pct": USAGE_THRESHOLDS},
    ))
    board = board.with_panel(table_panel(
        "Database limit usage",
        f"""SELECT last("numbackends") AS "used", max("numbackends") AS "peak",
                   last("effective_conn_limit") AS "limit", last("datconnlimit") AS "datconnlimit",
                   last("usage_pct") AS "usage_pct", max("usage_pct") AS "peak_pct"
            FROM "pg_db_limits" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY "db_instance", "datname" """,
        description="datconnlimit = -1 means unlimited: the server limit is used. peak = max over the time range.",
        w=12, h=8, sort_by="peak_pct",
        units={"usage_pct": "percent", "peak_pct": "percent"},
        thresholds={"usage_pct": USAGE_THRESHOLDS, "peak_pct": USAGE_THRESHOLDS},
    ))
    board = board.with_panel(table_panel(
        "Role limit usage",
        f"""SELECT last("current") AS "used", max("current") AS "peak",
                   last("effective_conn_limit") AS "limit", last("rolconnlimit") AS "rolconnlimit",
                   last("usage_pct") AS "usage_pct", max("usage_pct") AS "peak_pct"
            FROM "pg_role_limits" WHERE {where(F_INSTANCE)} GROUP BY "db_instance", "rolname" """,
        description="rolconnlimit = -1 means unlimited: the server limit is used.",
        w=12, h=8, sort_by="peak_pct",
        units={"usage_pct": "percent", "peak_pct": "percent"},
        thresholds={"usage_pct": USAGE_THRESHOLDS, "peak_pct": USAGE_THRESHOLDS},
    ))

    # ---- trends (FR9: time series only where the trend matters)
    board = board.with_panel(timeseries_panel(
        "Connections by state",
        f"""SELECT sum("cnt") FROM (
                SELECT max("cnt") AS "cnt" FROM "pg_activity_grouped"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), * fill(none)
            ) GROUP BY time($__interval), "db_instance", "state" fill(0)""",
        interval="15s",
    ))
    board = board.with_panel(timeseries_panel(
        "Database limit usage %",
        f"""SELECT max("usage_pct") FROM "pg_db_limits" WHERE {where(F_INSTANCE, F_DATNAME)}
            GROUP BY time($__interval), "db_instance", "datname" fill(none)""",
        unit="percent", interval="30s",
    ))

    # ---- grouped usage (FR4)
    board = board.with_panel(table_panel(
        "Grouped connections",
        f"""SELECT max("cnt") AS "peak_cnt", mean("cnt") AS "avg_cnt",
                   max("max_xact_age_s") AS "oldest_xact_s", max("max_state_age_s") AS "oldest_state_s"
            FROM "pg_activity_grouped" WHERE {where(F_INSTANCE, F_DATNAME)}
            GROUP BY "db_instance", "datname", "usename", "application_name", "state", "wait_event_type" """,
        description="One row per (instance, database, user, application, state, wait event type) over the range. "
                    "idle in transaction with a large oldest_xact_s is a leak.",
        h=12, sort_by="peak_cnt",
        units={"oldest_xact_s": "s", "oldest_state_s": "s", "avg_cnt": "none"},
        thresholds={"oldest_xact_s": (60, 300)},
    ))
    board = board.with_panel(table_panel(
        "By application and state",
        f"""SELECT sum("cnt") AS "peak_cnt" FROM (
                SELECT max("cnt") AS "cnt" FROM "pg_activity_grouped"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY *
            ) GROUP BY "db_instance", "application_name", "usename", "state" """,
        description="Pool sizing view: many idle vs. few active per application means an oversized pool.",
        w=12, h=10, sort_by="peak_cnt",
    ))
    board = board.with_panel(table_panel(
        "By user",
        f"""SELECT sum("cnt") AS "peak_cnt" FROM (
                SELECT max("cnt") AS "cnt" FROM "pg_activity_grouped"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY *
            ) GROUP BY "db_instance", "usename" """,
        w=12, h=10, sort_by="peak_cnt",
    ))

    # ---- runbooks (FR8)
    board = board.with_row(runbook_row("Connection exhaustion", "connection-exhaustion"))
    board = board.with_row(runbook_row("Idle-in-transaction leaks", "idle-in-transaction"))
    board = board.with_row(runbook_row("Pool misconfiguration", "pool-misconfiguration"))
    return board
