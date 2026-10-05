"""ch-overview: pg-overview on ClickHouse - health of every instance / database, links to the detailed boards."""
from builder.clickhouse import (
    F_DATNAME, F_ENV, F_INSTANCE, UID_CONNECTIONS, UID_INDEXES, UID_OVERVIEW, UID_STATEMENTS, base_dashboard, div,
    gauge_query, increase, last, rate_query, runbook_row, series_query, stat_panel, table_panel, timeseries_panel,
    var_datname, var_env, var_instance,
)

KEEP = "${__url_time_range}&var-env=${__data.fields.env}&var-db_instance=${__data.fields.db_instance}"
DB_SERIES = ("env", "db_instance", "datname")
DB_FILTERS = (F_ENV, F_INSTANCE, F_DATNAME)


def _db_rate(title: str, column: str, unit: str, description: str = ""):
    return timeseries_panel(
        title, rate_query("pg_db_stat", {column: column}, DB_FILTERS, DB_SERIES, DB_SERIES),
        unit=unit, interval="1m", description=description,
    )


def build():
    board = (
        base_dashboard(
            UID_OVERVIEW,
            "PostgreSQL (ClickHouse) / Overview",
            "Start here: limits, throughput, cache, temp files, locks. Drill down via links in the tables.",
        )
        .with_variable(var_env())
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    # ---- key numbers
    board = board.with_panel(stat_panel(
        "Max server connection usage",
        series_query("pg_settings_limits", {"usage": div(last("client_backends"), last("effective_limit"), "100 * ")},
                     (F_ENV, F_INSTANCE), ("env", "db_instance"), group_by=(), agg="max"),
        unit="percent", warn=70, crit=90,
    ))
    board = board.with_panel(stat_panel(
        "Blocked sessions (peak)",
        series_query("pg_locks_blocked", {"blocked": "max(blocked)"}, DB_FILTERS, DB_SERIES, group_by=(), agg="max"),
        warn=1, crit=5,
    ))
    board = board.with_panel(stat_panel(
        "Deadlocks (range)",
        series_query("pg_db_stat", {"deadlocks": increase("deadlocks")}, DB_FILTERS, DB_SERIES, group_by=()),
        warn=1, crit=10,
    ))
    board = board.with_panel(stat_panel(
        "Temp written (range)",
        series_query("pg_db_stat", {"temp_bytes": increase("temp_bytes")}, DB_FILTERS, DB_SERIES, group_by=()),
        unit="bytes",
    ))

    # ---- main table
    board = board.with_panel(table_panel(
        "Databases",
        series_query(
            "pg_db_stat",
            {"commits": increase("xact_commit"), "rollbacks": increase("xact_rollback"),
             "blks_hit": increase("blks_hit"), "blks_read": increase("blks_read"),
             "temp_files": increase("temp_files"), "temp_bytes": increase("temp_bytes"),
             "deadlocks": increase("deadlocks"), "sessions_killed": increase("sessions_killed"),
             "backends": last("numbackends")},
            DB_FILTERS, DB_SERIES,
            extra={"cache_hit_pct": div("blks_hit", "(blks_hit + blks_read)", "100 * ")},
        ),
        description="Counters over the selected time range (increase, resets counted from 0). "
                    "Click an instance to open Connections.",
        h=9, sort_by="commits",
        units={"cache_hit_pct": "percent", "temp_bytes": "bytes"},
        links={"db_instance": ("Connections", f"/d/{UID_CONNECTIONS}?{KEEP}")},
    ))

    # ---- trends
    board = board.with_panel(_db_rate("Commits / s", "xact_commit", "ops"))
    board = board.with_panel(_db_rate(
        "Blocks read from disk / s", "blks_read", "short",
        description="Growth means the working set no longer fits shared_buffers / OS cache."))
    board = board.with_panel(_db_rate("Temp bytes / s", "temp_bytes", "Bps"))
    board = board.with_panel(timeseries_panel(
        "Blocked sessions",
        gauge_query("pg_locks_blocked", "blocked", DB_FILTERS, DB_SERIES, DB_SERIES, outer="max"),
        interval="15s",
    ))

    # ---- navigation
    board = board.with_panel(table_panel(
        "Instances",
        series_query(
            "pg_settings_limits",
            {"version": last("server_version_num"), "max_connections": last("max_connections"),
             "shared_buffers": last("shared_buffers_bytes"), "work_mem": last("work_mem_bytes"),
             "statement_timeout_ms": last("statement_timeout_ms"),
             "idle_in_tx_timeout_ms": last("idle_in_transaction_session_timeout_ms"),
             "pgss_max": last("pg_stat_statements_max")},
            (F_ENV, F_INSTANCE), ("env", "db_instance"),
        ),
        description="Configuration context. Links: Statements / Indexes for the instance.",
        h=7,
        units={"shared_buffers": "bytes", "work_mem": "bytes"},
        links={
            "db_instance": ("Statements", f"/d/{UID_STATEMENTS}?{KEEP}"),
            "version": ("Indexes", f"/d/{UID_INDEXES}?{KEEP}"),
        },
    ))

    # ---- runbooks
    board = board.with_row(runbook_row("Lock waits / blocking", "lock-blocking"))
    board = board.with_row(runbook_row("Cache hit drop", "cache-hit-drop"))
    board = board.with_row(runbook_row("Temp file spills", "temp-file-spills"))
    return board
