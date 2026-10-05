"""Shared helpers for the pg-* dashboards (grafana-foundation-sdk + InfluxQL).

The SDK has no InfluxDB query builder, so `InfluxQL` implements the minimal Dataquery contract
(an object with `to_json()`, which the SDK JSONEncoder calls).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grafana_foundation_sdk.builders import common, dashboard, table, text, timeseries, stat
from grafana_foundation_sdk.cog import builder as cogbuilder
from grafana_foundation_sdk.cog import variants as cogvariants
from grafana_foundation_sdk.cog.encoder import JSONEncoder
from grafana_foundation_sdk.models import common as common_models
from grafana_foundation_sdk.models import dashboard as dm
from grafana_foundation_sdk.models import text as text_models

ROOT = Path(__file__).resolve().parents[2]
RUNBOOKS_DIR = ROOT / "docs" / "runbooks"
OUTPUT_DIR = ROOT / "config" / "grafana" / "provisioning" / "dashboards" / "json"

DATASOURCE = dm.DataSourceRef(type_val="influxdb", uid="pg-monitoring")
TAG = "pg-runbooks"

# Stable dashboard UIDs (DECISIONS.md D8) - drill-down links depend on them.
UID_OVERVIEW = "pg-overview"
UID_CONNECTIONS = "pg-connections"
UID_STATEMENTS = "pg-statements"
UID_STATEMENT_DETAIL = "pg-statement-detail"
UID_INDEXES = "pg-indexes"

# InfluxQL filters shared by all panels
F_ENV = 'env =~ /^$env$/'
F_INSTANCE = 'db_instance =~ /^$db_instance$/'
F_DATNAME = 'datname =~ /^$datname$/'
F_USENAME = 'usename =~ /^$usename$/'

# Variables kept by self-filter links (order = order in the URL)
FILTER_VARS = ("env", "db_instance", "datname", "usename")

# Series key of the per-user / per-database counters: env first, two envs may reuse an instance name (D22)
SERIES = ("env", "db_instance", "datname", "usename")

# Retention policies of pg_monitoring (DECISIONS.md D16): raw 7d (default) or 1h rollups for 200d
RETENTION_POLICIES = ("7d", "200d")


def src(measurement: str) -> str:
    """FROM target in the retention policy selected by the `rp` variable."""
    return f'"$rp"."{measurement}"'


class _InfluxQLQuery(cogvariants.Dataquery):
    def __init__(self, ref_id: str, query: str, result_format: str, alias: str = "") -> None:
        self.ref_id = ref_id
        self.query = query
        self.result_format = result_format
        self.alias = alias

    def to_json(self) -> dict[str, Any]:
        data = {
            "refId": self.ref_id,
            "datasource": {"type": DATASOURCE.type_val, "uid": DATASOURCE.uid},
            "query": self.query,
            "rawQuery": True,
            "resultFormat": self.result_format,
        }
        if self.alias:
            data["alias"] = self.alias
        return data


class InfluxQL(cogbuilder.Builder[cogvariants.Dataquery]):
    """Raw InfluxQL target. result_format: 'table' or 'time_series'; alias: legend, e.g. '$tag_datname'."""

    def __init__(self, query: str, ref_id: str = "A", result_format: str = "table", alias: str = "") -> None:
        self._q = _InfluxQLQuery(ref_id, " ".join(query.split()), result_format, alias)

    def build(self) -> cogvariants.Dataquery:
        return self._q


def influx_target(query: str, ref_id: str, kind: str, alias: str = "") -> InfluxQL:
    """Panel target factory (kind: 'table' / 'timeseries'); ch-* boards pass their own (builder/clickhouse.py)."""
    return InfluxQL(query, ref_id=ref_id, result_format="time_series" if kind == "timeseries" else "table", alias=alias)


def where(*filters: str) -> str:
    return " AND ".join(("$timeFilter",) + filters)


def increase_query(fields: dict[str, str], measurement: str, filters: tuple[str, ...], group_by: tuple[str, ...] = (),
                   series: tuple[str, ...] = SERIES, step: str = "5m",
                   extra: dict[str, str] | None = None) -> str:
    """Increase of cumulative counters over $timeFilter, summed per breakdown (DECISIONS.md D14b).

    fields: alias -> source counter. Inner query: non_negative_difference(last()) per series and step
    (resets / dealloc drops are ignored); outer query: sum() per `group_by`.
    extra:  alias -> expression over the summed aliases, e.g. {"mean_ms": 'sum("total_ms") / sum("calls")'}.
    """
    inner = ", ".join(f'non_negative_difference(last("{counter}")) AS "{alias}"' for alias, counter in fields.items())
    outer = [f'sum("{alias}") AS "{alias}"' for alias in fields]
    outer += [f'{expr} AS "{alias}"' for alias, expr in (extra or {}).items()]
    tags = ", ".join(f'"{t}"' for t in series)
    query = (f'SELECT {", ".join(outer)} FROM ('
             f'SELECT {inner} FROM {src(measurement)} WHERE {where(*filters)} '
             f'GROUP BY time({step}), {tags} fill(none))')
    if group_by:
        query += " GROUP BY " + ", ".join(f'"{t}"' for t in group_by)
    return query


def last_sum_query(field: str, measurement: str, filters: tuple[str, ...], group_by: tuple[str, ...] = (),
                   series: tuple[str, ...] = SERIES) -> str:
    """Gauge (not a counter): last value per series over $timeFilter, summed per `group_by`."""
    tags = ", ".join(f'"{t}"' for t in series)
    query = (f'SELECT sum("{field}") AS "{field}" FROM ('
             f'SELECT last("{field}") AS "{field}" FROM {src(measurement)} WHERE {where(*filters)} GROUP BY {tags})')
    if group_by:
        query += " GROUP BY " + ", ".join(f'"{t}"' for t in group_by)
    return query


# ---------------------------------------------------------------- variables
def var_rp() -> dashboard.CustomVariable:
    """Retention policy: 7d = raw points (15s / 1m / 10m, D7), 200d = 1h rollups. Must be the first variable."""
    default = RETENTION_POLICIES[0]
    return (
        dashboard.CustomVariable("rp")
        .label("Retention")
        .description("7d: raw points; 200d: 1h rollups (use ranges of days or more)")
        .values(",".join(RETENTION_POLICIES))
        .current(dm.VariableOption(text=default, value=default, selected=True))
        .options([dm.VariableOption(text=rp, value=rp, selected=rp == default) for rp in RETENTION_POLICIES])
    )


def var_env() -> dashboard.QueryVariable:
    """Environment (`env` tag = <ID>_ENV / PG_ENV of Telegraf), narrows the Instance list."""
    return (
        dashboard.QueryVariable("env")
        .label("Env")
        .datasource(DATASOURCE)
        .query(f'SHOW TAG VALUES FROM {src("pg_db_limits")} WITH KEY = "env"')
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
        .all_value(".*")
    )


def var_instance() -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable("db_instance")
        .label("Instance")
        .datasource(DATASOURCE)
        .query(f'SHOW TAG VALUES FROM {src("pg_db_limits")} WITH KEY = "db_instance" WHERE ' + F_ENV)
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
        .all_value(".*")
    )


def var_datname() -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable("datname")
        .label("Database")
        .datasource(DATASOURCE)
        .query(f'SHOW TAG VALUES FROM {src("pg_db_limits")} WITH KEY = "datname" WHERE ' + F_ENV + " AND " + F_INSTANCE)
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
        .all_value(".*")
    )


def var_usename() -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable("usename")
        .label("User")
        .datasource(DATASOURCE)
        .query(f'SHOW TAG VALUES FROM {src("pg_stmt_totals")} WITH KEY = "usename" WHERE '
               + " AND ".join((F_ENV, F_INSTANCE, F_DATNAME)))
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
        .all_value(".*")
    )


def var_textbox(name: str, label: str, default: str = ".*") -> dashboard.TextBoxVariable:
    """Free-text regex filter, filled by drill-down links (&var-<name>=...)."""
    return dashboard.TextBoxVariable(name).label(label).default_value(default)


# URL part carried by every link of the pg-* boards (the ch-* boards have no `rp` and pass keep="")
KEEP_RP = "&${rp:queryparam}"


def drill_url(uid: str, keep: str = KEEP_RP, **vars_from_fields: str) -> str:
    """URL to another board, carrying the time range, the retention policy and the given variables from row fields."""
    params = "&".join(f"var-{var}=${{__data.fields.{field}}}" for var, field in vars_from_fields.items())
    return f"/d/{uid}?${{__url_time_range}}{keep}&{params}"


def self_filter_url(uid: str, keep: str = KEEP_RP, **values: str) -> str:
    """URL to `uid` (usually the same board) that sets the given variables and keeps the other FILTER_VARS.

    values: variable -> interpolated value (e.g. '${__data.fields.datname}'). Variables not in `values`
    are carried as-is via ${var:queryparam} (multi-value and All are preserved) - DECISIONS.md D14c.
    """
    params = [f"var-{var}={values[var]}" if var in values else f"${{{var}:queryparam}}" for var in FILTER_VARS]
    params += [f"var-{var}={value}" for var, value in values.items() if var not in FILTER_VARS]
    return f"/d/{uid}?${{__url_time_range}}{keep}&" + "&".join(params)


def field_filter_url(uid: str, *fields: str, keep: str = KEEP_RP) -> str:
    """Table cell link: filter `uid` by the row values of `fields` (column name == variable name)."""
    return self_filter_url(uid, keep, **{f: f"${{__data.fields.{f}}}" for f in fields})


def series_filter_url(uid: str, *labels: str, keep: str = KEEP_RP) -> str:
    """Time series data link: filter `uid` by the series tag values (label name == variable name)."""
    return self_filter_url(uid, keep, **{label: f"${{__field.labels.{label}}}" for label in labels})


# ---------------------------------------------------------------- layout
def base_dashboard(uid: str, title: str, description: str, tag: str = TAG,
                   links_title: str = "PostgreSQL runbooks", extra_tags: tuple[str, ...] = ()) -> dashboard.Dashboard:
    return (
        dashboard.Dashboard(title)
        .uid(uid)
        .description(description)
        .tags([tag, "postgresql", *extra_tags])
        .time("now-3h", "now")
        .refresh("1m")
        .timezone("browser")
        .editable()
        .link(
            dashboard.DashboardLink(links_title)
            .type(dm.DashboardLinkType.DASHBOARDS)
            .tags([tag])
            .as_dropdown(True)
            .include_vars(True)
            .keep_time(True)
        )
    )


def runbook_row(title: str, *runbooks: str) -> dashboard.Row:
    """Collapsed row with the markdown of docs/runbooks/<name>.md (FR8)."""
    row = dashboard.Row(f"Runbook: {title}").collapsed(True)
    for name in runbooks:
        content = (RUNBOOKS_DIR / f"{name}.md").read_text(encoding="utf-8")
        row = row.with_panel(
            text.Panel()
            .title("")
            .mode(text_models.TextMode.MARKDOWN)
            .content(content)
            .grid_pos(dm.GridPos(h=14, w=24 // len(runbooks), x=0, y=0))
        )
    return row


def _organize(exclude: list[str], rename: dict[str, str] | None = None) -> dm.DataTransformerConfig:
    return dm.DataTransformerConfig(
        id_val="organize",
        options={"excludeByName": {name: True for name in exclude}, "renameByName": rename or {}},
    )


def table_panel(
    title: str,
    query: str | list[str],
    description: str = "",
    w: int = 24,
    h: int = 9,
    sort_by: str | None = None,
    units: dict[str, str] | None = None,
    links: dict[str, tuple[str, str]] | None = None,
    thresholds: dict[str, tuple[float, float]] | None = None,
    wrap: list[str] | None = None,
    datasource: dm.DataSourceRef = DATASOURCE,
    target=influx_target,
    transformations: list[dm.DataTransformerConfig] | None = None,
    merge: bool = True,
) -> table.Panel:
    """Table from one InfluxQL query (resultFormat=table).

    units:      column -> Grafana unit
    links:      column -> (title, url)  per-cell data link
    thresholds: column -> (warning, critical), colored background
    wrap:       columns with wrapped long text (query text)
    query:      one query or several (refId A, B, ...), rows are merged by equal tag columns
    transformations: applied after merge (env compare diffs, builder/compare.py); Time is then dropped before
                the merge too (the Time of last() differs between the queries)
    merge:      False -> the queries are combined by `transformations` (e.g. joinByField)
    """
    panel = table.Panel().title(title).description(description).datasource(datasource)
    for i, q in enumerate([query] if isinstance(query, str) else query):
        panel = panel.with_target(target(q, chr(ord("A") + i), "table"))
    if transformations is not None:
        panel = panel.with_transformation(_organize(["Time"]))
    if merge:
        panel = panel.with_transformation(dm.DataTransformerConfig(id_val="merge", options={}))
    panel = panel.with_transformation(_organize(["Time"])).grid_pos(dm.GridPos(h=h, w=w, x=0, y=0))
    for transformation in transformations or []:
        panel = panel.with_transformation(transformation)
    if sort_by:
        panel = panel.sort_by([_SortBy(sort_by)])
    for column, unit in (units or {}).items():
        panel = panel.override_by_name(column, [dm.DynamicConfigValue(id_val="unit", value=unit)])
    for column in wrap or []:
        panel = panel.override_by_name(
            column, [dm.DynamicConfigValue(id_val="custom.cellOptions", value={"type": "auto", "wrapText": True})]
        )
    for column, (link_title, url) in (links or {}).items():
        panel = panel.override_by_name(
            column, [dm.DynamicConfigValue(id_val="links", value=[{"title": link_title, "url": url}])]
        )
    for column, (warn, crit) in (thresholds or {}).items():
        panel = panel.override_by_name(
            column,
            [
                dm.DynamicConfigValue(
                    id_val="thresholds",
                    value={
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "orange", "value": warn},
                            {"color": "red", "value": crit},
                        ],
                    },
                ),
                dm.DynamicConfigValue(id_val="custom.cellOptions", value={"type": "color-background"}),
            ],
        )
    return panel


class _SortBy(cogbuilder.Builder[common_models.TableSortByFieldState]):
    def __init__(self, name: str) -> None:
        self._s = common_models.TableSortByFieldState(display_name=name, desc=True)

    def build(self) -> common_models.TableSortByFieldState:
        return self._s


def timeseries_panel(title: str, query: str, unit: str = "short", description: str = "",
                     w: int = 12, h: int = 8, interval: str = "", stacked: bool = False,
                     links: list[tuple[str, str]] | None = None, alias: str = "",
                     datasource: dm.DataSourceRef = DATASOURCE, target=influx_target) -> timeseries.Panel:
    """links: (title, url) data links on every series (url may use ${__field.labels.<tag>})."""
    panel = (
        timeseries.Panel()
        .title(title)
        .description(description)
        .datasource(datasource)
        .with_target(target(query, "A", "timeseries", alias))
        .unit(unit)
        .fill_opacity(10)
        .grid_pos(dm.GridPos(h=h, w=w, x=0, y=0))
    )
    if interval:
        panel = panel.interval(interval)
    if stacked:
        panel = panel.stacking(common.StackingConfig().mode(common_models.StackingMode.NORMAL)).fill_opacity(40)
    if links:
        panel = panel.override_by_regexp(".*", [dm.DynamicConfigValue(
            id_val="links", value=[{"title": t, "url": u} for t, u in links])])
    return panel


def stat_panel(title: str, query: str, unit: str = "short", description: str = "",
               w: int = 6, h: int = 4, warn: float | None = None, crit: float | None = None,
               datasource: dm.DataSourceRef = DATASOURCE, target=influx_target) -> stat.Panel:
    panel = (
        stat.Panel()
        .title(title)
        .description(description)
        .datasource(datasource)
        .with_target(target(query, "A", "table"))
        .unit(unit)
        .grid_pos(dm.GridPos(h=h, w=w, x=0, y=0))
    )
    if warn is not None and crit is not None:
        panel = panel.thresholds(
            dashboard.ThresholdsConfig()
            .mode(dm.ThresholdsMode.ABSOLUTE)
            .steps([
                dm.Threshold(value=None, color="green"),
                dm.Threshold(value=warn, color="orange"),
                dm.Threshold(value=crit, color="red"),
            ])
        )
    return panel


# ---------------------------------------------------------------- output
def layout(board: dashboard.Dashboard) -> dict[str, Any]:
    """Serialize and assign gridPos top-to-bottom (panels keep their w/h, flow left-to-right)."""
    data = json.loads(JSONEncoder(sort_keys=True).encode(board.build()))
    x = y = row_h = 0
    for p in data.get("panels", []):
        gp = p.setdefault("gridPos", {"h": 8, "w": 24})
        w, h = gp.get("w", 24), gp.get("h", 8)
        if p.get("type") == "row" or x + w > 24:
            x, y = 0, y + row_h
            row_h = 0
        gp.update({"x": x, "y": y})
        if p.get("type") == "row":
            y, row_h = y + 1, 0
            for i, inner in enumerate(p.get("panels", [])):
                inner.setdefault("gridPos", {}).update({"x": 0, "y": y + i * 14})
            continue
        x, row_h = x + w, max(row_h, h)
    for i, p in enumerate(data.get("panels", []), start=1):
        p["id"] = i
        for j, inner in enumerate(p.get("panels", []), start=1):
            inner["id"] = i * 100 + j
    return data


def write(board: dashboard.Dashboard, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(layout(board), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
