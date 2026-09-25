"""Generate all pg-* dashboards into config/grafana/provisioning/dashboards/json/."""
import importlib
import sys

from builder.common import write

BOARDS = {
    "overview": "pg-overview.json",
    "connections": "pg-connections.json",
    "statements": "pg-statements.json",
    "statement_detail": "pg-statement-detail.json",
    "indexes": "pg-indexes.json",
}


def main() -> int:
    for module_name, filename in BOARDS.items():
        module = importlib.import_module(module_name)
        print(write(module.build(), filename))
    return 0


if __name__ == "__main__":
    sys.exit(main())
