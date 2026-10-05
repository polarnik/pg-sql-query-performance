"""Generate all pg-* (InfluxDB) and ch-* (ClickHouse) dashboards into config/grafana/provisioning/dashboards/json/."""
import importlib
import sys

from builder.common import write

BOARDS = {
    "overview": "pg-overview.json",
    "connections": "pg-connections.json",
    "statements": "pg-statements.json",
    "statement_detail": "pg-statement-detail.json",
    "indexes": "pg-indexes.json",
    "ch_overview": "ch-overview.json",
    "ch_connections": "ch-connections.json",
    "ch_statements": "ch-statements.json",
    "ch_statement_detail": "ch-statement-detail.json",
    "ch_indexes": "ch-indexes.json",
}


def main() -> int:
    for module_name, filename in BOARDS.items():
        module = importlib.import_module(module_name)
        print(write(module.build(), filename))
    return 0


if __name__ == "__main__":
    sys.exit(main())
