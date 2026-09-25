"""pg-overview: health of every instance / database on one screen, links to the detailed boards."""
from builder.common import (
    F_DATNAME, F_INSTANCE, UID_CONNECTIONS, UID_INDEXES, UID_OVERVIEW, UID_STATEMENTS, base_dashboard,
    runbook_row, stat_panel, table_panel, timeseries_panel, var_datname, var_instance, where,
)

KEEP = "${__url_time_range}&var-db_instance=${__data.fields.db_instance}"


def build():
    board = (
        base_dashboard(
            UID_OVERVIEW,
            "PostgreSQL / Overview",
            "Start here: limits, throughput, cache, temp files, locks. Drill down via links in the tables.",
        )
        .with_variable(var_instance())
        .with_variable(var_datname())
    )

    # ---- key numbers
    board = board.with_panel(stat_panel(
        "Max server connection usage",
        f"""SELECT max("usage") FROM (
                SELECT last("client_backends") / last("effective_limit") * 100 AS "usage"
                FROM "pg_settings_limits" WHERE {where(F_INSTANCE)} GROUP BY "db_instance")""",
        unit="percent", warn=70, crit=90,
    ))
    board = board.with_panel(stat_panel(
        "Blocked sessions (peak)",
        f"""SELECT max("blocked") FROM "pg_locks_blocked" WHERE {where(F_INSTANCE, F_DATNAME)}""",
        warn=1, crit=5,
    ))
    board = board.with_panel(stat_panel(
        "Deadlocks (range)",
        f"""SELECT sum("d") FROM (SELECT spread("deadlocks") AS "d" FROM "pg_db_stat"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY "db_instance", "datname")""",
        warn=1, crit=10,
    ))
    board = board.with_panel(stat_panel(
        "Temp written (range)",
        f"""SELECT sum("t") FROM (SELECT spread("temp_bytes") AS "t" FROM "pg_db_stat"
                WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY "db_instance", "datname")""",
        unit="bytes",
    ))

    # ---- main table
    board = board.with_panel(table_panel(
        "Databases",
        f"""SELECT spread("xact_commit") AS "commits", spread("xact_rollback") AS "rollbacks",
                   spread("blks_hit") / (spread("blks_hit") + spread("blks_read")) * 100 AS "cache_hit_pct",
                   spread("temp_files") AS "temp_files", spread("temp_bytes") AS "temp_bytes",
                   spread("deadlocks") AS "deadlocks", spread("sessions_killed") AS "sessions_killed",
                   last("numbackends") AS "backends"
            FROM "pg_db_stat" WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY "db_instance", "datname" """,
        description="Counters over the selected time range (spread). Click an instance to open Connections.",
        h=9, sort_by="commits",
        units={"cache_hit_pct": "percent", "temp_bytes": "bytes"},
        links={"db_instance": ("Connections", f"/d/{UID_CONNECTIONS}?{KEEP}")},
    ))

    # ---- trends
    board = board.with_panel(timeseries_panel(
        "Commits / s",
        f"""SELECT non_negative_derivative(last("xact_commit"), 1s) FROM "pg_db_stat"
            WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), "db_instance", "datname" fill(none)""",
        unit="ops", interval="1m",
    ))
    board = board.with_panel(timeseries_panel(
        "Blocks read from disk / s",
        f"""SELECT non_negative_derivative(last("blks_read"), 1s) FROM "pg_db_stat"
            WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), "db_instance", "datname" fill(none)""",
        unit="short", interval="1m",
        description="Growth means the working set no longer fits shared_buffers / OS cache.",
    ))
    board = board.with_panel(timeseries_panel(
        "Temp bytes / s",
        f"""SELECT non_negative_derivative(last("temp_bytes"), 1s) FROM "pg_db_stat"
            WHERE {where(F_INSTANCE, F_DATNAME)} GROUP BY time($__interval), "db_instance", "datname" fill(none)""",
        unit="Bps", interval="1m",
    ))
    board = board.with_panel(timeseries_panel(
        "Blocked sessions",
        f"""SELECT max("blocked") FROM "pg_locks_blocked" WHERE {where(F_INSTANCE, F_DATNAME)}
            GROUP BY time($__interval), "db_instance", "datname" fill(none)""",
        interval="15s",
    ))

    # ---- navigation
    board = board.with_panel(table_panel(
        "Instances",
        f"""SELECT last("server_version_num") AS "version", last("max_connections") AS "max_connections",
                   last("shared_buffers_bytes") AS "shared_buffers", last("work_mem_bytes") AS "work_mem",
                   last("statement_timeout_ms") AS "statement_timeout_ms",
                   last("idle_in_transaction_session_timeout_ms") AS "idle_in_tx_timeout_ms",
                   last("pg_stat_statements_max") AS "pgss_max"
            FROM "pg_settings_limits" WHERE {where(F_INSTANCE)} GROUP BY "db_instance" """,
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
