"""Shared helpers for the ch-* dashboards: the same boards as pg-*, read from ClickHouse (pg_monitoring.*)
through the grafana-clickhouse-datasource (uid pg-monitoring-ch, user `reader`).

The SDK has no ClickHouse query builder, so `ClickHouseSQL` implements the minimal Dataquery contract
(like `InfluxQL` in builder/common.py). Panels / runbook rows / layout are reused from builder/common.py.

SQL conventions:
- filters: `$__timeFilter(time)` + `$__conditionalAll(<col> IN (${var:singlequote}), $var)` (All -> 1=1, the
  plugin expands it in the browser); textbox regex variables -> match(<col>, '^(...)$').
- every aggregated column gets an inner alias `c_<name>` and is renamed in the outer query: ClickHouse resolves
  an alias equal to a column name inside other expressions of the same SELECT (nested aggregate errors).
- counters (spread / non_negative_difference in pg-*): `increase()` sums the positive steps of every series;
  on a decrease (pg_stat_statements / pg_stat_database reset, entry re-admitted after dealloc) the new value
  is counted (on_reset="value", one entry per series: pg_stmt) or the step is ignored (on_reset="ignore", sums
  over many entries that drop on dealloc: pg_stmt_totals, pg_stmt_mask, D14b).
  Delta panels are never negative.
"""
from __future__ import annotations

from functools import partial
from typing import Any

from grafana_foundation_sdk.builders import dashboard
from grafana_foundation_sdk.cog import builder as cogbuilder
from grafana_foundation_sdk.cog import variants as cogvariants
from grafana_foundation_sdk.models import dashboard as dm

from builder import common

CH_DATASOURCE = dm.DataSourceRef(type_val="grafana-clickhouse-datasource", uid="pg-monitoring-ch")
DB = "pg_monitoring"
TAG = "ch-runbooks"

# Stable dashboard UIDs - drill-down links depend on them.
UID_OVERVIEW = "ch-overview"
UID_CONNECTIONS = "ch-connections"
UID_STATEMENTS = "ch-statements"
UID_STATEMENT_DETAIL = "ch-statement-detail"
UID_INDEXES = "ch-indexes"

# grafana-clickhouse-datasource Format enum: 0 = time series (long -> wide, string columns become labels), 1 = table
_FORMAT = {"timeseries": 0, "table": 1}


class _ClickHouseQuery(cogvariants.Dataquery):
    def __init__(self, ref_id: str, sql: str, fmt: str) -> None:
        self.ref_id = ref_id
        self.sql = sql
        self.fmt = fmt

    def to_json(self) -> dict[str, Any]:
        return {
            "refId": self.ref_id,
            "datasource": {"type": CH_DATASOURCE.type_val, "uid": CH_DATASOURCE.uid},
            "editorType": "sql",
            "rawSql": self.sql,
            "format": _FORMAT[self.fmt],
            "queryType": self.fmt,
        }


class ClickHouseSQL(cogbuilder.Builder[cogvariants.Dataquery]):
    """Raw ClickHouse SQL target. fmt: 'table' or 'timeseries' (first column = time, ordered by time)."""

    def __init__(self, ref_id: str, sql: str, fmt: str = "table") -> None:
        self._q = _ClickHouseQuery(ref_id, " ".join(sql.split()), fmt)

    def build(self) -> cogvariants.Dataquery:
        return self._q


def ch_target(query: str, ref_id: str, kind: str, alias: str = "") -> ClickHouseSQL:
    """Target factory for builder/common panels (alias is InfluxQL-only: series are named by their label columns)."""
    return ClickHouseSQL(ref_id, query, kind)


table_panel = partial(common.table_panel, datasource=CH_DATASOURCE, target=ch_target)
timeseries_panel = partial(common.timeseries_panel, datasource=CH_DATASOURCE, target=ch_target)
stat_panel = partial(common.stat_panel, datasource=CH_DATASOURCE, target=ch_target)
runbook_row = common.runbook_row
var_textbox = common.var_textbox

# links: same as pg-* without the retention policy variable
drill_url = partial(common.drill_url, keep="")
field_filter_url = partial(common.field_filter_url, keep="")
series_filter_url = partial(common.series_filter_url, keep="")


def base_dashboard(uid: str, title: str, description: str) -> dashboard.Dashboard:
    return common.base_dashboard(uid, title, description + " Source: ClickHouse pg_monitoring (dual write).",
                                 tag=TAG, links_title="PostgreSQL runbooks (ClickHouse)", extra_tags=("clickhouse",))


# ---------------------------------------------------------------- filters
def f_in(column: str, var: str | None = None) -> str:
    """Multi-value variable filter; no commas inside: $__conditionalAll splits its arguments on them."""
    var = var or column
    return f"$__conditionalAll({column} IN (${{{var}:singlequote}}), ${var})"


def f_regex(column: str, var: str | None = None) -> str:
    """Textbox variable holding a regex (default .*), anchored like the pg-* boards (=~ /^...$/)."""
    var = var or column
    return f"match({column}, concat('^(', ${{{var}:sqlstring}}, ')$'))"


F_ENV = f_in("env")
F_INSTANCE = f_in("db_instance")
F_DATNAME = f_in("datname")
F_USENAME = f_in("usename")


def where(*filters: str, time_filter: bool = True) -> str:
    return " AND ".join((("$__timeFilter(time)",) if time_filter else ()) + filters) or "1"


def table(name: str) -> str:
    return f"{DB}.{name}"


# ---------------------------------------------------------------- aggregates (use inside GROUP BY series)
def last(column: str) -> str:
    return f"argMax({column}, time)"


def increase(column: str, on_reset: str = "value") -> str:
    """Increase of a cumulative counter within the group over the range (replaces InfluxQL spread()).

    on_reset="value":  a decrease is a reset, the new value is the increase since the reset.
    on_reset="ignore": a decrease is ignored (sums over many entries that drop on dealloc: pg_stmt_totals,
                       pg_stmt_mask, D14b).
    """
    values = f"arraySort((v, t) -> t, groupArray(toFloat64({column})), groupArray(time))"
    if on_reset == "ignore":
        return f"arraySum(arrayMap(d -> greatest(d, 0), arrayDifference({values})))"
    return f"arraySum(arrayMap((d, v) -> if(d < 0, v, d), arrayDifference({values}), {values}))"


def div(a: str, b: str, scale: str = "") -> str:
    """a / b, NULL (empty cell) when b = 0."""
    return f"{scale}{a} / nullIf({b}, 0)"


# ---------------------------------------------------------------- query builders
def series_query(measurement: str, exprs: dict[str, str], filters: tuple[str, ...], series: tuple[str, ...],
                 group_by: tuple[str, ...] | None = None, extra: dict[str, str] | None = None, agg: str = "sum",
                 outer_where: str = "", time_filter: bool = True) -> str:
    """Two-level table query.

    inner: one row per `series` with exprs (alias -> aggregate over the raw rows, e.g. increase(), last()).
    outer: group_by=None -> the series rows as-is; otherwise `agg`(alias) per group_by (() = one row).
    extra: alias -> expression over the outer aliases, e.g. {"mean_ms": div("total_ms", "calls")}.
    outer_where: condition over the outer aliases (only with group_by=None).
    """
    keys = ", ".join(series)
    inner = ", ".join(f"{expr} AS c_{alias}" for alias, expr in exprs.items())
    sub = (f"SELECT {keys}, {inner} FROM {table(measurement)} WHERE {where(*filters, time_filter=time_filter)} "
           f"GROUP BY {keys}")
    if group_by is None:
        cols = list(series) + [f"c_{alias} AS {alias}" for alias in exprs]
    else:
        cols = list(group_by) + [f"{agg}(c_{alias}) AS {alias}" for alias in exprs]
    cols += [f"{expr} AS {alias}" for alias, expr in (extra or {}).items()]
    query = f"SELECT {', '.join(cols)} FROM ({sub})"
    if outer_where:
        query += f" WHERE {outer_where}"
    if group_by:
        query += " GROUP BY " + ", ".join(group_by)
    return query


def rate_query(measurement: str, counters: dict[str, str], filters: tuple[str, ...], series: tuple[str, ...],
               group_by: tuple[str, ...], values: dict[str, str] | None = None, per_second: bool = True,
               on_reset: str = "ignore") -> str:
    """Time series of counter changes per $__timeInterval bucket (non_negative_derivative / _difference in pg-*).

    counters: alias -> cumulative counter column; the last value per series and bucket is differenced with the
              previous bucket of the same series (lagInFrame), negative steps -> 0 (or the new value, on_reset).
    values:   output alias -> expression over {alias} placeholders = the per-bucket increase of each series,
              default: sum({alias}) / seconds (per_second) or sum({alias}), per `group_by`.
    """
    keys = ", ".join(series)
    last_values = ", ".join(f"argMax({column}, time) AS c_{alias}" for alias, column in counters.items())
    lags = ", ".join(f"c_{alias}, lagInFrame(c_{alias}, 1, c_{alias}) OVER w AS p_{alias}" for alias in counters)
    if on_reset == "ignore":
        deltas = {alias: f"greatest(c_{alias} - p_{alias}, 0)" for alias in counters}
    else:
        deltas = {alias: f"if(c_{alias} < p_{alias}, c_{alias}, c_{alias} - p_{alias})" for alias in counters}
    seconds = "dateDiff('second', pt, t)"
    if values is None:
        values = {alias: f"sum({{{alias}}} / {seconds})" if per_second else f"sum({{{alias}}})" for alias in counters}
    outer = ", ".join(f"{expr.format(**deltas)} AS {alias}" for alias, expr in values.items())
    by = "".join(f", {tag}" for tag in group_by)
    return (f"SELECT t AS time{by}, {outer} FROM ("
            f"SELECT t, {keys}, lagInFrame(t, 1, t) OVER w AS pt, {lags} FROM ("
            f"SELECT $__timeInterval(time) AS t, {keys}, {last_values} FROM {table(measurement)} "
            f"WHERE {where(*filters)} GROUP BY t, {keys}) "
            f"WINDOW w AS (PARTITION BY {keys} ORDER BY t ROWS BETWEEN 1 PRECEDING AND CURRENT ROW)"
            f") WHERE t > pt GROUP BY t{by} ORDER BY t")


def gauge_query(measurement: str, column: str, filters: tuple[str, ...], series: tuple[str, ...],
                group_by: tuple[str, ...], name: str = "", inner: str = "max", outer: str = "sum") -> str:
    """Time series of a gauge: `inner` per series and bucket, then `outer` per group_by."""
    keys = ", ".join(series)
    by = "".join(f", {tag}" for tag in group_by)
    return (f"SELECT t AS time{by}, {outer}(c) AS {name or column} FROM ("
            f"SELECT $__timeInterval(time) AS t, {keys}, {inner}({column}) AS c FROM {table(measurement)} "
            f"WHERE {where(*filters)} GROUP BY t, {keys}"
            f") GROUP BY t{by} ORDER BY t")


# ---------------------------------------------------------------- variables
def _query_variable(name: str, label: str, sql: str) -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable(name)
        .label(label)
        .datasource(CH_DATASOURCE)
        .query(" ".join(sql.split()))
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
    )


def var_env() -> dashboard.QueryVariable:
    """Environment (`env` column = <ID>_ENV / PG_ENV of Telegraf), narrows the Instance list."""
    return _query_variable("env", "Env", f"""
        SELECT DISTINCT env FROM {table("pg_db_limits")} WHERE {where()} ORDER BY env""")


def var_instance() -> dashboard.QueryVariable:
    return _query_variable("db_instance", "Instance", f"""
        SELECT DISTINCT db_instance FROM {table("pg_db_limits")} WHERE {where(F_ENV)} ORDER BY db_instance""")


def var_datname() -> dashboard.QueryVariable:
    return _query_variable("datname", "Database", f"""
        SELECT DISTINCT datname FROM {table("pg_db_limits")} WHERE {where(F_ENV, F_INSTANCE)} ORDER BY datname""")


def var_usename() -> dashboard.QueryVariable:
    return _query_variable("usename", "User", f"""
        SELECT DISTINCT usename FROM {table("pg_stmt_totals")} WHERE {where(F_ENV, F_INSTANCE, F_DATNAME)}
        ORDER BY usename""")
