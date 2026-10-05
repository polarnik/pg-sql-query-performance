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
    # env comparison (D23)
    "compare_tables": "pg-cmp-tables.json",
    "ch_compare_tables": "ch-cmp-tables.json",
    "compare_indexes": "pg-cmp-indexes.json",
    "ch_compare_indexes": "ch-cmp-indexes.json",
    "compare_statements": "pg-cmp-statements.json",
    "ch_compare_statements": "ch-cmp-statements.json",
    "compare_schema": "pg-cmp-schema.json",
    "ch_compare_schema": "ch-cmp-schema.json",
}


def main() -> int:
    for module_name, filename in BOARDS.items():
        module = importlib.import_module(module_name)
        print(write(module.build(), filename))
    return 0


if __name__ == "__main__":
    sys.exit(main())
