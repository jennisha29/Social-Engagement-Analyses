from __future__ import annotations

import csv
from pathlib import Path

from supplyflow.config import LocalPaths


WAREHOUSE_TABLES = [
    "dim_date",
    "dim_region",
    "dim_location",
    "dim_customer",
    "dim_product_category",
    "dim_product",
    "dim_carrier",
    "dim_service_level",
    "fact_shipments",
]

MART_TABLES = [
    "carrier_performance",
    "delivery_risk_summary",
    "fact_shipments",
    "profitability_by_region_category",
]


def count_rows(path: Path) -> int:
    with path.open(newline="") as file:
        return sum(1 for _ in csv.DictReader(file))


def require_table(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected table: {path}")
    rows = count_rows(path)
    if rows == 0:
        raise ValueError(f"Table has no rows: {path}")
    return rows


def main() -> None:
    paths = LocalPaths()
    print("SupplyFlow validation")
    print("=====================")

    print("Warehouse tables")
    for table in WAREHOUSE_TABLES:
        rows = require_table(paths.warehouse_dir / f"{table}.csv")
        print(f"- {table}: {rows:,} rows")

    print("Dashboard marts")
    for table in MART_TABLES:
        rows = require_table(paths.marts_dir / f"{table}.csv")
        print(f"- {table}: {rows:,} rows")

    print("Status: OK")


if __name__ == "__main__":
    main()
