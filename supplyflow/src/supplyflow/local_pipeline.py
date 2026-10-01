from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from supplyflow.config import LocalPaths
from supplyflow.synthetic_data import generate


def read_table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def write_table(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write empty table: {path}")
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in rows}


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def date_key(value: str | date) -> int:
    parsed = value if isinstance(value, date) else parse_date(value)
    return int(parsed.strftime("%Y%m%d"))


def read_sources(paths: LocalPaths) -> dict[str, list[dict[str, str]]]:
    required = {
        "orders": paths.orders_path,
        "shipments": paths.shipments_path,
        "carriers": paths.carriers_path,
        "customers": paths.customers_path,
        "products": paths.products_path,
        "locations": paths.locations_path,
    }
    if any(not path.exists() for path in required.values()):
        generate(rows=2500, seed=42, paths=paths)
    return {name: read_table(path) for name, path in required.items()}


def build_fact_shipments(tables: dict[str, list[dict[str, str]]]) -> list[dict[str, object]]:
    orders = index_by(tables["orders"], "order_id")
    carriers = index_by(tables["carriers"], "carrier_id")
    products = index_by(tables["products"], "product_id")
    customers = index_by(tables["customers"], "customer_id")
    locations = index_by(tables["locations"], "location_id")
    facts = []

    for shipment in tables["shipments"]:
        order = orders[shipment["order_id"]]
        carrier = carriers[shipment["carrier_id"]]
        product = products[order["product_id"]]
        customer = customers[order["customer_id"]]
        destination = locations[order["destination_location_id"]]
        ship_date = parse_date(shipment["ship_date"])
        promised_date = parse_date(shipment["promised_delivery_date"])
        actual_date = parse_date(shipment["actual_delivery_date"])
        delivery_days = max((actual_date - ship_date).days, 0)
        late_days = max((actual_date - promised_date).days, 0)
        on_time = late_days == 0
        damage = shipment["damage_flag"].lower() == "true"
        revenue = float(order["revenue"])
        product_cost = float(order["product_cost"])
        shipping_cost = float(shipment["shipping_cost"])
        gross_profit = round(revenue - product_cost - shipping_cost, 2)
        risk_score = min(
            100,
            late_days * 18
            + (0 if on_time else 25)
            + (30 if damage else 0)
            + {"standard": 5, "expedited": 12, "same_day": 20}.get(order["service_level"], 0),
        )

        facts.append(
            {
                "shipment_id": shipment["shipment_id"],
                "order_id": shipment["order_id"],
                "customer_id": order["customer_id"],
                "product_id": order["product_id"],
                "carrier_id": shipment["carrier_id"],
                "origin_location_id": order["origin_location_id"],
                "destination_location_id": order["destination_location_id"],
                "order_date": order["order_date"],
                "order_date_key": date_key(order["order_date"]),
                "ship_date": shipment["ship_date"],
                "ship_date_key": date_key(shipment["ship_date"]),
                "promised_delivery_date": shipment["promised_delivery_date"],
                "promised_delivery_date_key": date_key(shipment["promised_delivery_date"]),
                "actual_delivery_date": shipment["actual_delivery_date"],
                "actual_delivery_date_key": date_key(shipment["actual_delivery_date"]),
                "service_level": order["service_level"],
                "mode": carrier["mode"],
                "quantity": int(order["quantity"]),
                "distance_miles": int(shipment["distance_miles"]),
                "revenue": round(revenue, 2),
                "product_cost": round(product_cost, 2),
                "shipping_cost": round(shipping_cost, 2),
                "gross_profit": gross_profit,
                "profit_margin": round(gross_profit / revenue, 4) if revenue else 0,
                "delivery_days": delivery_days,
                "late_days": late_days,
                "on_time_flag": on_time,
                "damage_flag": damage,
                "delivery_risk_score": risk_score,
                "category": product["category"],
                "customer_segment": customer["customer_segment"],
                "destination_region": destination["region"],
            }
        )
    return sorted(facts, key=lambda row: (row["order_date"], row["shipment_id"]))


def build_dim_date(facts: list[dict[str, object]]) -> list[dict[str, object]]:
    dates = {
        parse_date(str(row[column]))
        for row in facts
        for column in ["order_date", "ship_date", "promised_delivery_date", "actual_delivery_date"]
    }
    if dates:
        cursor = min(dates)
        end = max(dates)
        while cursor <= end:
            dates.add(cursor)
            cursor += timedelta(days=1)

    rows = []
    for value in sorted(dates):
        rows.append(
            {
                "date_key": date_key(value),
                "full_date": value.isoformat(),
                "year": value.year,
                "quarter": (value.month - 1) // 3 + 1,
                "month": value.month,
                "week": value.isocalendar().week,
                "day_of_month": value.day,
                "is_weekend": value.weekday() >= 5,
            }
        )
    return rows


def build_dim_region(tables: dict[str, list[dict[str, str]]]) -> list[dict[str, object]]:
    regions = sorted(
        {
            row["region"]
            for table_name in ["locations", "customers"]
            for row in tables[table_name]
            if row.get("region")
        }
    )
    return [{"region_key": index, "region_name": region} for index, region in enumerate(regions, start=1)]


def build_dim_product_category(tables: dict[str, list[dict[str, str]]]) -> list[dict[str, object]]:
    categories = sorted({row["category"] for row in tables["products"]})
    return [{"category_key": index, "category_name": category} for index, category in enumerate(categories, start=1)]


def build_dim_service_level() -> list[dict[str, object]]:
    return [
        {"service_level_key": 1, "service_level": "standard", "promised_days": 6},
        {"service_level_key": 2, "service_level": "expedited", "promised_days": 3},
        {"service_level_key": 3, "service_level": "same_day", "promised_days": 1},
    ]


def build_warehouse_tables(
    tables: dict[str, list[dict[str, str]]], facts: list[dict[str, object]]
) -> dict[str, list[dict[str, object]]]:
    dim_region = build_dim_region(tables)
    dim_product_category = build_dim_product_category(tables)
    dim_service_level = build_dim_service_level()
    region_keys = {row["region_name"]: row["region_key"] for row in dim_region}
    category_keys = {row["category_name"]: row["category_key"] for row in dim_product_category}
    service_level_keys = {row["service_level"]: row["service_level_key"] for row in dim_service_level}

    dim_location = [
        {
            "location_id": row["location_id"],
            "region_key": region_keys[row["region"]],
            "city": row["city"],
            "state": row["state"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "location_type": row["location_type"],
        }
        for row in tables["locations"]
    ]
    dim_customer = [
        {
            "customer_id": row["customer_id"],
            "customer_segment": row["customer_segment"],
            "region_key": region_keys[row["region"]],
            "priority_score": row["priority_score"],
        }
        for row in tables["customers"]
    ]
    dim_product = [
        {
            "product_id": row["product_id"],
            "category_key": category_keys[row["category"]],
            "product_name": row["product_name"],
            "unit_cost": row["unit_cost"],
            "unit_price": row["unit_price"],
            "weight_lb": row["weight_lb"],
        }
        for row in tables["products"]
    ]
    fact_shipments = [
        {
            "shipment_id": row["shipment_id"],
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "product_id": row["product_id"],
            "carrier_id": row["carrier_id"],
            "origin_location_id": row["origin_location_id"],
            "destination_location_id": row["destination_location_id"],
            "order_date_key": row["order_date_key"],
            "ship_date_key": row["ship_date_key"],
            "promised_delivery_date_key": row["promised_delivery_date_key"],
            "actual_delivery_date_key": row["actual_delivery_date_key"],
            "order_date": row["order_date"],
            "ship_date": row["ship_date"],
            "promised_delivery_date": row["promised_delivery_date"],
            "actual_delivery_date": row["actual_delivery_date"],
            "service_level_key": service_level_keys[row["service_level"]],
            "quantity": row["quantity"],
            "distance_miles": row["distance_miles"],
            "revenue": row["revenue"],
            "product_cost": row["product_cost"],
            "shipping_cost": row["shipping_cost"],
            "gross_profit": row["gross_profit"],
            "profit_margin": row["profit_margin"],
            "delivery_days": row["delivery_days"],
            "late_days": row["late_days"],
            "on_time_flag": row["on_time_flag"],
            "damage_flag": row["damage_flag"],
            "delivery_risk_score": row["delivery_risk_score"],
        }
        for row in facts
    ]

    return {
        "dim_date": build_dim_date(facts),
        "dim_region": dim_region,
        "dim_location": dim_location,
        "dim_customer": dim_customer,
        "dim_product_category": dim_product_category,
        "dim_product": dim_product,
        "dim_carrier": tables["carriers"],
        "dim_service_level": dim_service_level,
        "fact_shipments": fact_shipments,
    }


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_summary(
    facts: list[dict[str, object]],
    keys: list[str],
    aggregations: dict[str, tuple[str, str]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in facts:
        grouped[tuple(row[key] for key in keys)].append(row)

    output = []
    for key_values, rows in grouped.items():
        summary = dict(zip(keys, key_values))
        for output_name, (source_column, method) in aggregations.items():
            values = [row[source_column] for row in rows]
            if method == "count":
                summary[output_name] = len(values)
            elif method == "sum":
                summary[output_name] = round(sum(float(value) for value in values), 2)
            elif method == "mean":
                summary[output_name] = round(average([float(value) for value in values]), 4)
            elif method == "false_rate":
                summary[output_name] = round(1 - average([1.0 if value else 0.0 for value in values]), 4)
        output.append(summary)
    return sorted(output, key=lambda row: tuple(str(row[key]) for key in keys))


def write_curated_tables(paths: LocalPaths, tables: dict[str, list[dict[str, str]]], facts: list[dict[str, object]]) -> None:
    paths.curated_dir.mkdir(parents=True, exist_ok=True)
    paths.marts_dir.mkdir(parents=True, exist_ok=True)
    paths.warehouse_dir.mkdir(parents=True, exist_ok=True)

    warehouse_tables = build_warehouse_tables(tables, facts)
    for name, rows in warehouse_tables.items():
        write_table(paths.warehouse_dir / f"{name}.csv", rows)

    for source_name, warehouse_name in [
        ("carriers", "dim_carrier"),
        ("customers", "dim_customer"),
        ("products", "dim_product"),
        ("locations", "dim_location"),
    ]:
        write_table(paths.curated_dir / f"{warehouse_name}.csv", warehouse_tables[warehouse_name])
    write_table(paths.facts_path, facts)
    write_table(
        paths.marts_dir / "carrier_performance.csv",
        build_summary(
            facts,
            ["carrier_id", "mode"],
            {
                "shipments": ("shipment_id", "count"),
                "avg_delivery_days": ("delivery_days", "mean"),
                "on_time_failure_rate": ("on_time_flag", "false_rate"),
                "damage_rate": ("damage_flag", "mean"),
                "total_shipping_cost": ("shipping_cost", "sum"),
            },
        ),
    )
    write_table(
        paths.marts_dir / "profitability_by_region_category.csv",
        build_summary(
            facts,
            ["category", "destination_region"],
            {
                "revenue": ("revenue", "sum"),
                "gross_profit": ("gross_profit", "sum"),
                "avg_margin": ("profit_margin", "mean"),
            },
        ),
    )
    write_table(
        paths.marts_dir / "delivery_risk_summary.csv",
        build_summary(
            facts,
            ["destination_region", "service_level"],
            {
                "avg_risk": ("delivery_risk_score", "mean"),
                "late_rate": ("on_time_flag", "false_rate"),
            },
        ),
    )


def run(paths: LocalPaths) -> Path:
    tables = read_sources(paths)
    facts = build_fact_shipments(tables)
    write_curated_tables(paths, tables, facts)
    return paths.facts_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local SupplyFlow curation pipeline.")
    parser.parse_args()
    output_path = run(LocalPaths())
    print(f"Built SupplyFlow mart: {output_path}")


if __name__ == "__main__":
    main()
