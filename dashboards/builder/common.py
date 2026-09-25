"""Shared helpers for the pg-* dashboards (grafana-foundation-sdk + InfluxQL).

The SDK has no InfluxDB query builder, so `InfluxQL` implements the minimal Dataquery contract
(an object with `to_json()`, which the SDK JSONEncoder calls).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grafana_foundation_sdk.builders import dashboard, table, text, timeseries, stat
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
F_INSTANCE = 'db_instance =~ /^$db_instance$/'
F_DATNAME = 'datname =~ /^$datname$/'


class _InfluxQLQuery(cogvariants.Dataquery):
    def __init__(self, ref_id: str, query: str, result_format: str) -> None:
        self.ref_id = ref_id
        self.query = query
        self.result_format = result_format

    def to_json(self) -> dict[str, Any]:
        return {
            "refId": self.ref_id,
            "datasource": {"type": DATASOURCE.type_val, "uid": DATASOURCE.uid},
            "query": self.query,
            "rawQuery": True,
            "resultFormat": self.result_format,
        }


class InfluxQL(cogbuilder.Builder[cogvariants.Dataquery]):
    """Raw InfluxQL target. result_format: 'table' or 'time_series'."""

    def __init__(self, query: str, ref_id: str = "A", result_format: str = "table") -> None:
        self._q = _InfluxQLQuery(ref_id, " ".join(query.split()), result_format)

    def build(self) -> cogvariants.Dataquery:
        return self._q


def where(*filters: str) -> str:
    return " AND ".join(("$timeFilter",) + filters)


# ---------------------------------------------------------------- variables
def var_instance() -> dashboard.QueryVariable:
    return (
        dashboard.QueryVariable("db_instance")
        .label("Instance")
        .datasource(DATASOURCE)
        .query('SHOW TAG VALUES FROM "pg_db_limits" WITH KEY = "db_instance"')
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
        .query('SHOW TAG VALUES FROM "pg_db_limits" WITH KEY = "datname" WHERE ' + F_INSTANCE)
        .refresh(dm.VariableRefresh.ON_TIME_RANGE_CHANGED)
        .sort(dm.VariableSort.ALPHABETICAL_ASC)
        .multi(True)
        .include_all(True)
        .all_value(".*")
    )


def var_textbox(name: str, label: str, default: str = ".*") -> dashboard.TextBoxVariable:
    """Free-text regex filter, filled by drill-down links (&var-<name>=...)."""
    return dashboard.TextBoxVariable(name).label(label).default_value(default)


def drill_url(uid: str, **vars_from_fields: str) -> str:
    """URL to another board, carrying the time range and the given variables from row fields."""
    params = "&".join(f"var-{var}=${{__data.fields.{field}}}" for var, field in vars_from_fields.items())
    return f"/d/{uid}?${{__url_time_range}}&{params}"


# ---------------------------------------------------------------- layout
def base_dashboard(uid: str, title: str, description: str) -> dashboard.Dashboard:
    return (
        dashboard.Dashboard(title)
        .uid(uid)
        .description(description)
        .tags([TAG, "postgresql"])
        .time("now-3h", "now")
        .refresh("1m")
        .timezone("browser")
        .editable()
        .link(
            dashboard.DashboardLink("PostgreSQL runbooks")
            .type(dm.DashboardLinkType.DASHBOARDS)
            .tags([TAG])
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
    query: str,
    description: str = "",
    w: int = 24,
    h: int = 9,
    sort_by: str | None = None,
    units: dict[str, str] | None = None,
    links: dict[str, tuple[str, str]] | None = None,
    thresholds: dict[str, tuple[float, float]] | None = None,
    wrap: list[str] | None = None,
) -> table.Panel:
    """Table from one InfluxQL query (resultFormat=table).

    units:      column -> Grafana unit
    links:      column -> (title, url)  per-cell data link
    thresholds: column -> (warning, critical), colored background
    wrap:       columns with wrapped long text (query text)
    """
    panel = (
        table.Panel()
        .title(title)
        .description(description)
        .datasource(DATASOURCE)
        .with_target(InfluxQL(query))
        .with_transformation(dm.DataTransformerConfig(id_val="merge", options={}))
        .with_transformation(_organize(["Time"]))
        .grid_pos(dm.GridPos(h=h, w=w, x=0, y=0))
    )
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
                     w: int = 12, h: int = 8, interval: str = "") -> timeseries.Panel:
    panel = (
        timeseries.Panel()
        .title(title)
        .description(description)
        .datasource(DATASOURCE)
        .with_target(InfluxQL(query, result_format="time_series"))
        .unit(unit)
        .fill_opacity(10)
        .grid_pos(dm.GridPos(h=h, w=w, x=0, y=0))
    )
    if interval:
        panel = panel.interval(interval)
    return panel


def stat_panel(title: str, query: str, unit: str = "short", description: str = "",
               w: int = 6, h: int = 4, warn: float | None = None, crit: float | None = None) -> stat.Panel:
    panel = (
        stat.Panel()
        .title(title)
        .description(description)
        .datasource(DATASOURCE)
        .with_target(InfluxQL(query))
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
