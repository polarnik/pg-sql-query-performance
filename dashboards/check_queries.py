"""Run every panel query of the generated dashboards through Grafana (/api/ds/query) for every retention
policy (variable rp, D16) and report errors / empty results.
Usage: .venv/bin/python check_queries.py [grafana_url] [time_from]"""
import base64
import json
import sys
import urllib.request

from builder.common import OUTPUT_DIR, RETENTION_POLICIES

GRAFANA = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
FROM = sys.argv[2] if len(sys.argv) > 2 else "now-1h"
AUTH = "Basic " + base64.b64encode(b"admin:admin").decode()
VARS = {"$db_instance": ".*", "$datname": ".*", "$usename": ".*", "$query_mask_md5": ".*", "$query_md5": ".*",
        "$schemaname": ".*", "$relname": ".*"}


def panels(board):
    for p in board.get("panels", []):
        yield p
        yield from p.get("panels", [])


def run(target, rp):
    query = target["query"]
    for k, v in {**VARS, "$rp": rp}.items():
        query = query.replace(k, v)
    body = {"from": FROM, "to": "now",
            "queries": [dict(target, query=query, intervalMs=60000, maxDataPoints=500)]}
    req = urllib.request.Request(f"{GRAFANA}/api/ds/query", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": AUTH})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.load(resp)["results"][target["refId"]]
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read()[:200]!r}", 0
    if res.get("error"):
        return res["error"], 0
    rows = sum(len((f.get("data", {}).get("values") or [[]])[0]) for f in res.get("frames", []))
    return None, rows


def main() -> int:
    failed = 0
    for path in sorted(OUTPUT_DIR.glob("pg-*.json")):
        board = json.loads(path.read_text())
        for rp in RETENTION_POLICIES:
            for p in panels(board):
                for t in p.get("targets", []):
                    err, rows = run(t, rp)
                    status = "ERROR" if err else ("EMPTY" if rows == 0 else "ok")
                    failed += status == "ERROR"
                    print(f"{status:5} {rp:4} {board['uid']:20} {p.get('title', '')[:40]:40} rows={rows} {err or ''}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
