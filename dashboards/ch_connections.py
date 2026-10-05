"""ch-connections: pg-connections on ClickHouse - connection limits (server / database / role) and grouped usage."""
from builder.clickhouse import (
    F_DATNAME, F_ENV, F_INSTANCE, UID_CONNECTIONS, base_dashboard, div, gauge_query, last, runbook_row,
    series_query, table_panel, timeseries_panel, var_datname, var_env, var_instance,
)

USAGE_THRESHOLDS = (70, 90)
DB_FILTERS = (F_ENV, F_INSTANCE, F_DATNAME)
# every tag of pg_activity_grouped = one series
ACTIVITY = ("env", "db_instance", "datname", "usename", "application_name", "state", "wait_event_type")


def _peak_by(title: str, group_by: tuple[str, ...], **kwargs):
    """Peak connections per series over the range, summed per group_by."""
    return table_panel(
        title, series_query("pg_activity_grouped", {"peak_cnt": "max(cnt)"}, DB_FILTERS, ACTIVITY, group_by=group_by),
        sort_by="peak_cnt", **kwargs,
    )


def build():
    board = (
        base_dashboard(
            UID_CONNECTIONS,
            "PostgreSQL (ClickHouse) / Connections",
            "Connection limits and usage grouped by state, application and user. See docs/runbooks.",
        )
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    # ---- limits (FR3)
    board = board.with_panel(table_panel(
        "Server limit usage",
        series_query(
            "pg_settings_limits",
            {"used": last("client_backends"), "limit": last("effective_limit"),
             "max_connections": last("max_connections"), "superuser_reserved": last("superuser_reserved"),
             "reserved": last("reserved")},
            (F_ENV, F_INSTANCE), ("env", "db_instance"),
            extra={"usage_pct": div("used", "limit", "100 * ")},
        ),
        description="effective limit = max_connections - superuser_reserved_connections - reserved_connections "
                    "(5 min sample).",
        w=24, h=6, sort_by="usage_pct",
        units={"usage_pct": "percent"}, thresholds={"usage_pct": USAGE_THRESHOLDS},
    ))
    board = board.with_panel(table_panel(
        "Database limit usage",
        series_query(
            "pg_db_limits",
            {"used": last("numbackends"), "peak": "max(numbackends)", "limit": last("effective_conn_limit"),
             "datconnlimit": last("datconnlimit"), "usage_pct": last("usage_pct"), "peak_pct": "max(usage_pct)"},
            DB_FILTERS, ("env", "db_instance", "datname"),
        ),
        description="datconnlimit = -1 means unlimited: the server limit is used. peak = max over the time range.",
        w=12, h=8, sort_by="peak_pct",
        units={"usage_pct": "percent", "peak_pct": "percent"},
        thresholds={"usage_pct": USAGE_THRESHOLDS, "peak_pct": USAGE_THRESHOLDS},
    ))
    board = board.with_panel(table_panel(
        "Role limit usage",
        series_query(
            "pg_role_limits",
            {"used": last("current"), "peak": "max(current)", "limit": last("effective_conn_limit"),
             "rolconnlimit": last("rolconnlimit"), "usage_pct": last("usage_pct"), "peak_pct": "max(usage_pct)"},
            (F_ENV, F_INSTANCE), ("env", "db_instance", "rolname"),
        ),
        description="rolconnlimit = -1 means unlimited: the server limit is used.",
        w=12, h=8, sort_by="peak_pct",
        units={"usage_pct": "percent", "peak_pct": "percent"},
        thresholds={"usage_pct": USAGE_THRESHOLDS, "peak_pct": USAGE_THRESHOLDS},
    ))

    # ---- trends (FR9: time series only where the trend matters)
    board = board.with_panel(timeseries_panel(
        "Connections by state",
        gauge_query("pg_activity_grouped", "cnt", DB_FILTERS, ACTIVITY, ("env", "db_instance", "state")),
        interval="15s",
    ))
    board = board.with_panel(timeseries_panel(
        "Database limit usage %",
        gauge_query("pg_db_limits", "usage_pct", DB_FILTERS, ("env", "db_instance", "datname"),
                    ("env", "db_instance", "datname"), outer="max"),
        unit="percent", interval="30s",
    ))

    # ---- grouped usage (FR4)
    board = board.with_panel(table_panel(
        "Grouped connections",
        series_query(
            "pg_activity_grouped",
            {"peak_cnt": "max(cnt)", "avg_cnt": "avg(cnt)", "oldest_xact_s": "max(max_xact_age_s)",
             "oldest_state_s": "max(max_state_age_s)"},
            DB_FILTERS, ACTIVITY,
        ),
        description="One row per (instance, database, user, application, state, wait event type) over the range. "
                    "idle in transaction with a large oldest_xact_s is a leak.",
        h=12, sort_by="peak_cnt",
        units={"oldest_xact_s": "s", "oldest_state_s": "s", "avg_cnt": "none"},
        thresholds={"oldest_xact_s": (60, 300)},
    ))
    board = board.with_panel(_peak_by(
        "By application and state", ("env", "db_instance", "application_name", "usename", "state"),
        description="Pool sizing view: many idle vs. few active per application means an oversized pool.",
        w=12, h=10,
    ))
    board = board.with_panel(_peak_by("By user", ("env", "db_instance", "usename"), w=12, h=10))

    # ---- runbooks (FR8)
    board = board.with_row(runbook_row("Connection exhaustion", "connection-exhaustion"))
    board = board.with_row(runbook_row("Idle-in-transaction leaks", "idle-in-transaction"))
    board = board.with_row(runbook_row("Pool misconfiguration", "pool-misconfiguration"))
    return board
