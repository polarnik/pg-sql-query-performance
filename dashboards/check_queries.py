"""Run every panel query of the generated dashboards through Grafana (/api/ds/query) and report errors / empty results.

pg-* (default): every InfluxQL query (variables and panels) for every retention policy (variable rp, D16);
  multi-value variables = .*, the single-value env_a / env_b of the pg-cmp-* boards = the first / last env.
ch-* (--clickhouse): every ClickHouse SQL through the pg-monitoring-ch datasource, i.e. as the ClickHouse user
  `reader`. Variable queries run first (they are checked too); panels run twice: all variables = All
  ($__conditionalAll -> 1=1) and = the first value of each variable (the IN (...) filters).
Single-value variables (env_a / env_b / db_instance of the *-cmp-* boards) take CHECK_VARS values when set, e.g.
  CHECK_VARS=env_a=perf,env_b=prod,db_instance=facade (an instance of both envs, so both sides have rows).
Usage: .venv/bin/python check_queries.py [--clickhouse] [--only=<uid prefix>] [grafana_url] [time_from]"""
import os
import base64
import json
import re
import sys
import urllib.request

from builder.common import OUTPUT_DIR, RETENTION_POLICIES

CLICKHOUSE = "--clickhouse" in sys.argv
ONLY = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")), "")
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OVERRIDES = dict(kv.split("=", 1) for kv in os.environ.get("CHECK_VARS", "").split(",") if "=" in kv)
GRAFANA = ARGS[0] if len(ARGS) > 0 else "http://localhost:3000"
FROM = ARGS[1] if len(ARGS) > 1 else "now-1h"
AUTH = "Basic " + base64.b64encode(b"admin:admin").decode()
VARS = {"$env": ".*", "$db_instance": ".*", "$datname": ".*", "$usename": ".*", "$query_mask_md5": ".*",
        "$query_md5": ".*", "$schemaname": ".*", "$relname": ".*"}


def panels(board):
    for p in board.get("panels", []):
        yield p
        yield from p.get("panels", [])


def query_api(target):
    """POST one target to /api/ds/query -> (error, frames)."""
    body = {"from": FROM, "to": "now", "queries": [dict(target, intervalMs=60000, maxDataPoints=500)]}
    req = urllib.request.Request(f"{GRAFANA}/api/ds/query", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": AUTH})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.load(resp)["results"][target["refId"]]
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read()[:300]!r}", []
    return res.get("error"), res.get("frames", [])


def count_rows(frames):
    return sum(len((f.get("data", {}).get("values") or [[]])[0]) for f in frames)


def influx_target(query, ref_id="A"):
    return {"refId": ref_id, "datasource": {"uid": "pg-monitoring"}, "query": query, "rawQuery": True,
            "resultFormat": "table"}


def envs(rp):
    """Values of the env tag (for env_a / env_b)."""
    _, frames = query_api(influx_target(f'SHOW TAG VALUES FROM "{rp}"."pg_db_limits" WITH KEY = "env"'))
    values = frames[0]["data"]["values"][-1] if frames and frames[0]["data"]["values"] else []
    return values or [""]


def run(target, rp, env_values=("",)):
    query = target["query"]
    values = {**VARS, "$env_a": env_values[0], "$env_b": env_values[-1], "$rp": rp,
              **{f"${var}": value for var, value in OVERRIDES.items()}}
    for k in sorted(values, key=len, reverse=True):  # $env_a before $env
        query = query.replace(k, values[k])
    err, frames = query_api(dict(target, query=query))
    return err, count_rows(frames)


# ---------------------------------------------------------------- ClickHouse
def _macro_args(sql, start):
    """Arguments of the macro call whose '(' is at `start` -> (args, end index after ')')."""
    depth, args, current = 0, [], ""
    for i in range(start, len(sql)):
        ch = sql[i]
        if ch == "(":
            depth += 1
            if depth == 1:
                continue
        elif ch == ")":
            depth -= 1
            if depth == 0:
                args.append(current)
                return args, i + 1
        elif ch == "," and depth == 1:
            args.append(current)
            current = ""
            continue
        current += ch
    raise ValueError(f"unbalanced macro in {sql[:80]}")


def interpolate(sql, values, textboxes):
    """Frontend-side interpolation of the ClickHouse plugin + Grafana (values: var -> list or None = All)."""
    macro = "$__conditionalAll("
    while (pos := sql.find(macro)) != -1:
        args, end = _macro_args(sql, pos + len(macro) - 1)
        var = re.search(r"\$\{?(\w+)", args[1]).group(1)
        sql = sql[:pos] + ("1=1" if values.get(var) is None else args[0]) + sql[end:]
    for var, vals in values.items():
        quoted = ",".join("'" + str(v).replace("'", "\\'") + "'" for v in (vals or []))
        sql = sql.replace(f"${{{var}:singlequote}}", quoted or "''")
    for var, value in textboxes.items():
        sql = sql.replace(f"${{{var}:sqlstring}}", "'" + value.replace("'", "''") + "'")
    return sql


def ch_target(sql, ref_id="A", fmt=1):
    return {"refId": ref_id, "datasource": {"uid": "pg-monitoring-ch"}, "editorType": "sql", "format": fmt,
            "rawSql": sql}


def check_clickhouse():
    failed = 0
    for path in sorted(OUTPUT_DIR.glob(f"ch-{ONLY}*.json")):
        board = json.loads(path.read_text())
        uid = board["uid"]
        for mode in ("all", "first"):
            # variables in board order: a later query sees the earlier selections (All or the first value)
            values, textboxes = {}, {}
            for var in board.get("templating", {}).get("list", []):
                if var["type"] == "textbox":
                    textboxes[var["name"]] = var.get("query") or ".*"
                    continue
                err, frames = query_api(ch_target(interpolate(var["query"], values, textboxes)))
                options = frames[0]["data"]["values"][0] if frames and frames[0]["data"]["values"] else []
                if var["name"] in OVERRIDES:
                    values[var["name"]] = [OVERRIDES[var["name"]]]
                elif not var.get("includeAll"):  # single value: Grafana selects the first option
                    values[var["name"]] = options[:1]
                else:
                    values[var["name"]] = None if mode == "all" else options[:1]
                status = "ERROR" if err else ("EMPTY" if not options else "ok")
                failed += status == "ERROR"
                print(f"{status:5} {mode:5} {uid:20} {'$' + var['name']:40} values={options[:5]} {err or ''}")
            for p in panels(board):
                for t in p.get("targets", []):
                    err, frames = query_api(dict(t, rawSql=interpolate(t["rawSql"], values, textboxes)))
                    rows = count_rows(frames)
                    status = "ERROR" if err else ("EMPTY" if rows == 0 else "ok")
                    failed += status == "ERROR"
                    print(f"{status:5} {mode:5} {uid:20} {p.get('title', '')[:40]:40} rows={rows} {err or ''}")
    return 1 if failed else 0


def main() -> int:
    if CLICKHOUSE:
        return check_clickhouse()
    failed = 0
    for path in sorted(OUTPUT_DIR.glob(f"pg-{ONLY}*.json")):
        board = json.loads(path.read_text())
        for rp in RETENTION_POLICIES:
            env_values = envs(rp)
            for var in board.get("templating", {}).get("list", []):
                if var["type"] != "query":
                    continue
                err, rows = run(influx_target(var["query"]), rp, env_values)
                status = "ERROR" if err else ("EMPTY" if rows == 0 else "ok")
                failed += status == "ERROR"
                print(f"{status:5} {rp:4} {board['uid']:20} {'$' + var['name']:40} rows={rows} {err or ''}")
            for p in panels(board):
                for t in p.get("targets", []):
                    err, rows = run(t, rp, env_values)
                    status = "ERROR" if err else ("EMPTY" if rows == 0 else "ok")
                    failed += status == "ERROR"
                    print(f"{status:5} {rp:4} {board['uid']:20} {p.get('title', '')[:40]:40} rows={rows} {err or ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
