"""Shared helpers for the env comparison boards: the same Instance in two envs (Env A left, Env B right, D23).

pg-cmp-* read InfluxDB (pg_monitoring, variable rp), ch-cmp-* read ClickHouse. Every board has the variables
env_a / env_b (single value; env_b is sorted descending, so by default it differs from env_a), db_instance (single
value) and datname (multi, default All), and the dashboard links dropdown of the compare tag.

Panels:
- side_by_side(): two w=12 tables, one per env, sorted descending by the main metric.
- *_only_in(): objects present in one env only; *_delta(): objects in both envs with value_a / value_b / delta (B - A) /
  delta_pct, sorted by |delta|.
  InfluxDB (no joins): query A (columns *_a, env = $env_a) and query B (*_b) grouped by the same tags without env,
  outer-merged by Grafana (merge), then filterByValue / calculateField / sortBy.
  ClickHouse: one SQL, conditional aggregates per env over the per-object rows of both envs (pair_query()).
- *_share(): share_pct of the env total (activity differs between envs), InfluxDB: joinByField env with a total query,
  ClickHouse: window sum.
"""
from __future__ import annotations

from typing import Callable

from grafana_foundation_sdk.builders import dashboard, table
from grafana_foundation_sdk.models import dashboard as dm

from builder import clickhouse as ch
from builder import common

SIDES = ("a", "b")
OTHER = {"a": "b", "b": "a"}

# Stable dashboard UIDs (links between the compare boards and from their cells depend on them)
UID_TABLES = "pg-cmp-tables"
UID_INDEXES = "pg-cmp-indexes"
UID_STATEMENTS = "pg-cmp-statements"
UID_SCHEMA = "pg-cmp-schema"
CH_UID_TABLES = "ch-cmp-tables"
CH_UID_INDEXES = "ch-cmp-indexes"
CH_UID_STATEMENTS = "ch-cmp-statements"
CH_UID_SCHEMA = "ch-cmp-schema"

TAG = "pg-env-compare"
CH_TAG = "ch-env-compare"

# Variables carried by cell links between the compare boards
KEEP_VARS = ("env_a", "env_b", "db_instance", "datname")

DELTA_NOTE = (" delta = B - A, delta_pct = delta / A; sorted by |delta|."
              " Objects of one env only: see the Only in panels.")
TOP_N_NOTE = (" Collected top-N per instance (top 300 tables / 500 indexes / 200 statements): an object missing in"
              " one env may just be outside its top-N. Use a short range for composition checks"
              " (dropped objects stay in it).")

# ---------------------------------------------------------------- InfluxQL filters
F_SIDE = {"a": "env = '$env_a'", "b": "env = '$env_b'"}
F_INSTANCE = common.F_INSTANCE  # single value, regex keeps the pg-* filter form
F_DATNAME = common.F_DATNAME


def side_filters(side: str, *extra: str) -> tuple[str, ...]:
    return (F_SIDE[side], F_INSTANCE, F_DATNAME) + extra


# ---------------------------------------------------------------- ClickHouse filters
CH_SIDE = {"a": "env = ${env_a:singlequote}", "b": "env = ${env_b:singlequote}"}
CH_PAIR = "env IN (${env_a:singlequote}, ${env_b:singlequote})"
CH_INSTANCE = "db_instance = ${db_instance:singlequote}"
CH_DATNAME = ch.F_DATNAME


def ch_side_filters(side: str, *extra: str) -> tuple[str, ...]:
    return (CH_SIDE[side], CH_INSTANCE, CH_DATNAME) + extra


# ---------------------------------------------------------------- variables
def _influx_variable(name: str, label: str, query: str, sort: dm.VariableSort) -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable(name)
        .label(label)
        .datasource(common.DATASOURCE)
        .query(query)
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(sort)
    )


def _ch_variable(name: str, label: str, sql: str, sort: dm.VariableSort) -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable(name)
        .label(label)
        .datasource(ch.CH_DATASOURCE)
        .query(" ".join(sql.split()))
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(sort)
    )


def influx_variables() -> list:
    envs = f'SHOW TAG VALUES FROM {common.src("pg_db_limits")} WITH KEY = "env"'
    return [
        common.var_rp(),
        _influx_variable("env_a", "Env A", envs, dm.VariableSort.ALPHABETICAL_ASC),
        _influx_variable("env_b", "Env B", envs, dm.VariableSort.ALPHABETICAL_DESC),
        _influx_variable("db_instance", "Instance", f'SHOW TAG VALUES FROM {common.src("pg_db_limits")} '
                         f'WITH KEY = "db_instance" WHERE {F_SIDE["a"]}', dm.VariableSort.ALPHABETICAL_ASC),
        _influx_variable("datname", "Database", f'SHOW TAG VALUES FROM {common.src("pg_db_limits")} '
                         f'WITH KEY = "datname" WHERE env =~ /^($env_a|$env_b)$/ AND {F_INSTANCE}',
                         dm.VariableSort.ALPHABETICAL_ASC).multi(True).include_all(True).all_value(".*"),
    ]


def ch_variables() -> list:
    limits = ch.table("pg_db_limits")
    return [
        _ch_variable("env_a", "Env A", f"SELECT DISTINCT env FROM {limits} WHERE {ch.where()} ORDER BY env",
                     dm.VariableSort.ALPHABETICAL_ASC),
        _ch_variable("env_b", "Env B", f"SELECT DISTINCT env FROM {limits} WHERE {ch.where()} ORDER BY env DESC",
                     dm.VariableSort.ALPHABETICAL_DESC),
        # instances of env A, the ones present in both envs first
        _ch_variable("db_instance", "Instance", f"""
            SELECT db_instance FROM {limits} WHERE {ch.where(CH_PAIR)} GROUP BY db_instance
            HAVING countIf({CH_SIDE["a"]}) > 0 ORDER BY uniqExact(env) DESC, db_instance""",
                     dm.VariableSort.DISABLED),
        _ch_variable("datname", "Database", f"""
            SELECT DISTINCT datname FROM {limits} WHERE {ch.where(CH_PAIR, CH_INSTANCE)} ORDER BY datname""",
                     dm.VariableSort.ALPHABETICAL_ASC).multi(True).include_all(True),
    ]


# ---------------------------------------------------------------- boards
def base_dashboard(uid: str, title: str, description: str, clickhouse: bool = False,
                   extra_variables: tuple = ()) -> dashboard.Dashboard:
    """Compare board: links dropdown of the compare boards (keeps the variables) + of the runbook boards."""
    if clickhouse:
        board = common.base_dashboard(uid, title, description + " Source: ClickHouse pg_monitoring (dual write).",
                                      tag=CH_TAG, links_title="Env compare (ClickHouse)",
                                      extra_tags=("clickhouse", "env-compare"))
        runbooks, variables = (ch.TAG, "PostgreSQL runbooks (ClickHouse)"), ch_variables()
    else:
        board = common.base_dashboard(uid, title, description, tag=TAG, links_title="Env compare",
                                      extra_tags=("env-compare",))
        runbooks, variables = (common.TAG, "PostgreSQL runbooks"), influx_variables()
    board = board.link(
        dashboard.DashboardLink(runbooks[1])
        .type(dm.DashboardLinkType.DASHBOARDS)
        .tags([runbooks[0]])
        .as_dropdown(True)
        .keep_time(True)
    )
    for variable in [*variables, *extra_variables]:
        board = board.with_variable(variable)
    return board


def cell_url(uid: str, clickhouse: bool = False, **vars_from_fields: str) -> str:
    """Cell link to another compare board: keeps env_a / env_b / db_instance / datname, sets vars from row fields."""
    keep = "" if clickhouse else common.KEEP_RP
    params = [f"${{{var}:queryparam}}" for var in KEEP_VARS if var not in vars_from_fields]
    params += [f"var-{var}=${{__data.fields.{field}}}" for var, field in vars_from_fields.items()]
    return f"/d/{uid}?${{__url_time_range}}{keep}&" + "&".join(params)


# ---------------------------------------------------------------- transformations
def _t(id_val: str, options: dict) -> dm.DataTransformerConfig:
    return dm.DataTransformerConfig(id_val=id_val, options=options)


def _by_name(name: str) -> dict:
    return {"matcher": {"id": "byName", "options": name}}


def _binary(left: str, operator: str, right: str, alias: str) -> dm.DataTransformerConfig:
    return _t("calculateField", {"mode": "binary", "alias": alias,
                                 "binary": {"left": _by_name(left), "operator": operator, "right": _by_name(right)}})


def _abs(field: str, alias: str) -> dm.DataTransformerConfig:
    return _t("calculateField", {"mode": "unary", "alias": alias, "unary": {"operator": "abs", "fieldName": field}})


def _filter_null(fields: list[str], keep: bool, match: str = "any") -> dm.DataTransformerConfig:
    """keep=True: rows where `fields` are null (match any / all); keep=False: rows where they are not."""
    filters = [{"fieldName": f, "config": {"id": "isNull", "options": {}}} for f in fields]
    return _t("filterByValue", {"type": "include" if keep else "exclude", "match": match, "filters": filters})


def _sort(field: str) -> dm.DataTransformerConfig:
    return _t("sortBy", {"sort": [{"field": field, "desc": True}]})


def _organize(exclude: list[str], rename: dict[str, str] | None = None) -> dm.DataTransformerConfig:
    return _t("organize", {"excludeByName": {name: True for name in exclude}, "renameByName": rename or {}})


# ---------------------------------------------------------------- panels
def side_by_side(title: str, query: Callable[[str], str | list[str]], sort_by: str, clickhouse: bool = False,
                 h: int = 10, **table_kw) -> list[table.Panel]:
    """Env A (left) and Env B (right) tables; query(side) -> the query of one env ('a' / 'b').

    links may be a function side -> links (e.g. a drill-down to the env of the side).
    """
    panel = ch.table_panel if clickhouse else common.table_panel
    links = table_kw.pop("links", None)
    return [panel(f"{title} — ${{env_{side}}}", query(side), w=12, h=h, sort_by=sort_by,
                  links=links(side) if callable(links) else links, **table_kw)
            for side in SIDES]


def influx_share(query: str, value: str) -> tuple[list[str], dict]:
    """Per-object query (GROUP BY "env", ...) + its env total -> (queries, table_panel kwargs) adding share_pct."""
    total = f'SELECT sum("{value}") AS "env_total" FROM ({query}) GROUP BY "env"'
    return [query, total], {
        "merge": False,
        "transformations": [
            _t("joinByField", {"byField": "env", "mode": "inner"}),
            _binary(value, "/", "env_total", "share_pct"),
            _organize(["env", "env_total"]),
        ],
    }


def ch_share(query: str, value: str) -> str:
    """Adds share_pct = value / env total (one env per query)."""
    return f"SELECT *, {value} / nullIf(sum({value}) OVER (), 0) AS share_pct FROM ({query})"


def share_pair(title: str, query: Callable[[str], str], value: str, sort_by: str, clickhouse: bool = False,
               units: dict[str, str] | None = None, **table_kw) -> list[table.Panel]:
    """side_by_side() + share_pct = `value` / env total. InfluxDB: query(side) must GROUP BY "env" (join key)."""
    units = {"share_pct": "percentunit", **(units or {})}
    if clickhouse:
        return side_by_side(title, lambda side: ch_share(query(side), value), sort_by, clickhouse=True, units=units,
                            **table_kw)
    _, share_kw = influx_share(query("a"), value)
    return side_by_side(title, lambda side: influx_share(query(side), value)[0], sort_by, units=units,
                        **share_kw, **table_kw)


def influx_only_in(title: str, query: Callable[[str], str], side: str, values: tuple[str, ...], sort_by: str,
                   description: str = "", **table_kw) -> table.Panel:
    """Rows of query(side) without a row in the other env; query(s) names its value columns <value>_<s>."""
    other = OTHER[side]
    return common.table_panel(
        title or f"Only in ${{env_{side}}} (not in ${{env_{other}}})", [query("a"), query("b")],
        description=description, sort_by=sort_by, w=12,
        transformations=[
            _filter_null([f"{values[0]}_{other}"], keep=True),
            _organize([f"{v}_{other}" for v in values], {f"{v}_{side}": v for v in values}),
        ],
        **table_kw,
    )


def influx_delta(title: str, query: Callable[[str], str], value: str, extra_deltas: tuple[str, ...] = (),
                 description: str = "", units: dict[str, str] | None = None, text: str = "",
                 **table_kw) -> table.Panel:
    """Objects of both envs: <value>_a, <value>_b, delta (B - A), delta_pct, sorted by |delta| (+ <x>_delta).

    text: a text column of both queries (<text>_a / _b), shown once as <text>.
    """
    transformations = [
        _filter_null([f"{value}_a", f"{value}_b"], keep=False),
        _binary(f"{value}_b", "-", f"{value}_a", "delta"),
        _binary("delta", "/", f"{value}_a", "delta_pct"),
    ]
    transformations += [_binary(f"{x}_b", "-", f"{x}_a", f"{x}_delta") for x in extra_deltas]
    transformations += [_abs("delta", "abs_delta"), _sort("abs_delta"),
                        _organize(["abs_delta"] + ([f"{text}_b"] if text else []), {f"{text}_a": text} if text else {})]
    return common.table_panel(
        title, [query("a"), query("b")], description=description + DELTA_NOTE,
        units={"delta_pct": "percentunit", **(units or {})}, transformations=transformations, **table_kw,
    )


def pair_query(measurement: str, exprs: dict[str, str], keys: tuple[str, ...], filters: tuple[str, ...] = ()) -> str:
    """ClickHouse: one row per object of env A or B with <alias>_a / <alias>_b and n_a / n_b (rows per env)."""
    inner = ch.series_query(measurement, exprs, (CH_PAIR, CH_INSTANCE, CH_DATNAME) + filters, keys + ("env",))
    return pair_of(inner, keys, tuple(exprs))


def pair_of(rows: str, keys: tuple[str, ...], aliases: tuple[str, ...]) -> str:
    """pair_query() over a query with one row per (keys, env) and the columns `aliases`."""
    cols = list(keys)
    for alias in aliases:
        cols += [f"anyIf({alias}, {CH_SIDE['a']}) AS {alias}_a", f"anyIf({alias}, {CH_SIDE['b']}) AS {alias}_b"]
    cols += [f"countIf({CH_SIDE['a']}) AS n_a", f"countIf({CH_SIDE['b']}) AS n_b"]
    return f"SELECT {', '.join(cols)} FROM ({rows}) GROUP BY {', '.join(keys)}"


def ch_only_in(title: str, pair: str, keys: tuple[str, ...], side: str, values: tuple[str, ...], sort_by: str,
               description: str = "", **table_kw) -> table.Panel:
    other = OTHER[side]
    cols = list(keys) + [f"{v}_{side} AS {v}" for v in values]
    return ch.table_panel(
        title or f"Only in ${{env_{side}}} (not in ${{env_{other}}})",
        f"SELECT {', '.join(cols)} FROM ({pair}) WHERE n_{side} > 0 AND n_{other} = 0 ORDER BY {sort_by} DESC",
        description=description, sort_by=sort_by, w=12, **table_kw,
    )


def ch_delta(title: str, pair: str, keys: tuple[str, ...], value: str, extra_deltas: tuple[str, ...] = (),
             description: str = "", units: dict[str, str] | None = None, text: str = "", **table_kw) -> table.Panel:
    cols = list(keys) + [f"{value}_a", f"{value}_b", f"{value}_b - {value}_a AS delta",
                         f"{ch.div('delta', f'{value}_a')} AS delta_pct"]
    for x in extra_deltas:
        cols += [f"{x}_a", f"{x}_b", f"{x}_b - {x}_a AS {x}_delta"]
    if text:
        cols.append(f"{text}_a AS {text}")
    return ch.table_panel(
        title, f"SELECT {', '.join(cols)} FROM ({pair}) WHERE n_a > 0 AND n_b > 0 ORDER BY abs(delta) DESC",
        description=description + DELTA_NOTE, units={"delta_pct": "percentunit", **(units or {})}, **table_kw,
    )


def influx_changed(title: str, query: Callable[[str], str], present: str, flags: tuple[str, ...],
                   description: str = "", **table_kw) -> table.Panel:
    """Objects of both envs (`present`_a / _b not null) where any of `flags` differs between A and B."""
    transformations = [_filter_null([f"{present}_a", f"{present}_b"], keep=False)]
    transformations += [_binary(f"{flag}_b", "-", f"{flag}_a", f"{flag}_diff") for flag in flags]
    transformations += [
        _t("filterByValue", {"type": "exclude", "match": "all", "filters": [
            {"fieldName": f"{flag}_diff", "config": {"id": "equal", "options": {"value": 0}}} for flag in flags]}),
        _organize([f"{flag}_diff" for flag in flags]),
    ]
    return common.table_panel(title, [query("a"), query("b")], description=description,
                              transformations=transformations, **table_kw)


def ch_changed(title: str, pair: str, keys: tuple[str, ...], values: tuple[str, ...], flags: tuple[str, ...],
               description: str = "", **table_kw) -> table.Panel:
    cols = list(keys) + [f"{v}_{side}" for v in values for side in SIDES]
    differs = " OR ".join(f"{flag}_a != {flag}_b" for flag in flags)
    return ch.table_panel(
        title, f"SELECT {', '.join(cols)} FROM ({pair}) WHERE n_a > 0 AND n_b > 0 AND ({differs})",
        description=description, **table_kw,
    )


def schema_links(clickhouse: bool = False) -> dict[str, tuple[str, str]]:
    """schemaname / relname cells -> the Schema drill board of the row (keeps envs, instance)."""
    uid = CH_UID_SCHEMA if clickhouse else UID_SCHEMA
    return {
        "schemaname": ("Schema drill", cell_url(uid, clickhouse, datname="datname", schemaname="schemaname")),
        "relname": ("Schema drill: this table",
                    cell_url(uid, clickhouse, datname="datname", schemaname="schemaname", relname="relname")),
    }


# ---------------------------------------------------------------- Schema drill
F_SCHEMA = 'schemaname =~ /^$schemaname$/'  # single value
F_RELNAME = 'relname =~ /^$relname$/'
CH_SCHEMA = "schemaname = ${schemaname:singlequote}"
CH_RELNAME = ch.f_regex("relname")


def schema_variables(clickhouse: bool = False) -> tuple:
    """Schema (single value, schemas of both envs) + table regex textbox (default .*)."""
    if clickhouse:
        schema = _ch_variable("schemaname", "Schema", f"""
            SELECT DISTINCT schemaname FROM {ch.table("pg_table_stat")}
            WHERE {ch.where(CH_PAIR, CH_INSTANCE, CH_DATNAME)} ORDER BY schemaname""",
                              dm.VariableSort.ALPHABETICAL_ASC)
    else:
        schema = _influx_variable("schemaname", "Schema", f'SHOW TAG VALUES FROM {common.src("pg_table_stat")} '
                                  f'WITH KEY = "schemaname" WHERE env =~ /^($env_a|$env_b)$/ AND {F_INSTANCE} '
                                  f'AND {F_DATNAME}', dm.VariableSort.ALPHABETICAL_ASC)
    return schema, common.var_textbox("relname", "Table regex")
