from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from supplyflow.config import LocalPaths


REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
SERVICE_LEVELS = ["standard", "expedited", "same_day"]
PRODUCT_CATEGORIES = ["electronics", "home", "apparel", "grocery", "industrial"]


def weighted_choice(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    marker = rng.random()
    cumulative = 0.0
    for value, weight in choices:
        cumulative += weight
        if marker <= cumulative:
            return value
    return choices[-1][0]


def build_locations(rng: random.Random, count: int = 32) -> list[dict[str, object]]:
    cities = [
        ("Boston", "MA", "Northeast", 42.3601, -71.0589),
        ("New York", "NY", "Northeast", 40.7128, -74.0060),
        ("Atlanta", "GA", "Southeast", 33.7490, -84.3880),
        ("Miami", "FL", "Southeast", 25.7617, -80.1918),
        ("Chicago", "IL", "Midwest", 41.8781, -87.6298),
        ("Detroit", "MI", "Midwest", 42.3314, -83.0458),
        ("Dallas", "TX", "Southwest", 32.7767, -96.7970),
        ("Phoenix", "AZ", "Southwest", 33.4484, -112.0740),
        ("Los Angeles", "CA", "West", 34.0522, -118.2437),
        ("Seattle", "WA", "West", 47.6062, -122.3321),
    ]
    rows = []
    for index in range(1, count + 1):
        city, state, region, latitude, longitude = cities[(index - 1) % len(cities)]
        rows.append(
            {
                "location_id": f"LOC{index:03d}",
                "city": city,
                "state": state,
                "region": region,
                "latitude": round(latitude + rng.uniform(-0.22, 0.22), 5),
                "longitude": round(longitude + rng.uniform(-0.22, 0.22), 5),
                "location_type": "warehouse" if index <= 10 else "customer_zone",
            }
        )
    return rows


def build_dimension_tables(rng: random.Random) -> dict[str, list[dict[str, object]]]:
    carriers = [
        {
            "carrier_id": f"CAR{index:03d}",
            "carrier_name": name,
            "mode": mode,
            "contract_tier": tier,
            "base_cost_per_mile": cost,
        }
        for index, (name, mode, tier, cost) in enumerate(
            [
                ("Arrow Freight", "truckload", "gold", 2.15),
                ("BlueRiver Logistics", "ltl", "silver", 1.74),
                ("Northstar Air", "air", "gold", 5.85),
                ("Atlas Intermodal", "intermodal", "bronze", 1.52),
                ("Pioneer Express", "truckload", "silver", 2.02),
                ("MetroLink Freight", "ltl", "bronze", 1.61),
            ],
            start=1,
        )
    ]
    products = []
    for index in range(1, 41):
        category = rng.choice(PRODUCT_CATEGORIES)
        unit_cost = round(rng.uniform(8, 420), 2)
        products.append(
            {
                "product_id": f"SKU{index:04d}",
                "category": category,
                "product_name": f"{category.title()} Kit {index:02d}",
                "unit_cost": unit_cost,
                "unit_price": round(unit_cost * rng.uniform(1.18, 1.85), 2),
                "weight_lb": round(rng.uniform(0.5, 58), 2),
            }
        )
    customers = [
        {
            "customer_id": f"CUS{index:04d}",
            "customer_segment": rng.choice(["enterprise", "mid_market", "retail", "wholesale"]),
            "region": rng.choice(REGIONS),
            "priority_score": rng.randint(1, 5),
        }
        for index in range(1, 251)
    ]
    return {
        "locations": build_locations(rng),
        "carriers": carriers,
        "products": products,
        "customers": customers,
    }


def build_transactions(
    rng: random.Random,
    dimensions: dict[str, list[dict[str, object]]],
    rows: int,
) -> dict[str, list[dict[str, object]]]:
    start_date = date(2025, 1, 1)
    orders = []
    shipments = []
    warehouses = [row["location_id"] for row in dimensions["locations"] if row["location_type"] == "warehouse"]
    destinations = [row["location_id"] for row in dimensions["locations"] if row["location_type"] == "customer_zone"]

    for index in range(1, rows + 1):
        order_date = start_date + timedelta(days=rng.randint(0, 89))
        service_level = weighted_choice(rng, [("standard", 0.62), ("expedited", 0.28), ("same_day", 0.10)])
        quantity = rng.randint(1, 18)
        product = rng.choice(dimensions["products"])
        customer = rng.choice(dimensions["customers"])
        carrier = rng.choice(dimensions["carriers"])
        promised_days = {"standard": 6, "expedited": 3, "same_day": 1}[service_level]
        actual_days = max(1, round(rng.gauss(promised_days, 1.4)))
        distance_miles = rng.randint(70, 2700)
        service_multiplier = {"standard": 1.0, "expedited": 1.18, "same_day": 1.42}[service_level]
        freight_cost = distance_miles * float(carrier["base_cost_per_mile"]) * 0.075 * service_multiplier
        handling_cost = quantity * float(product["weight_lb"]) * rng.uniform(0.12, 0.28)
        shipping_cost = round((freight_cost + handling_cost) * rng.uniform(0.9, 1.18), 2)
        revenue = round(quantity * float(product["unit_price"]), 2)
        product_cost = round(quantity * float(product["unit_cost"]), 2)

        order_id = f"ORD{index:06d}"
        orders.append(
            {
                "order_id": order_id,
                "order_date": order_date.isoformat(),
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "origin_location_id": rng.choice(warehouses),
                "destination_location_id": rng.choice(destinations),
                "service_level": service_level,
                "quantity": quantity,
                "revenue": revenue,
                "product_cost": product_cost,
            }
        )
        shipments.append(
            {
                "shipment_id": f"SHP{index:06d}",
                "order_id": order_id,
                "carrier_id": carrier["carrier_id"],
                "ship_date": (order_date + timedelta(days=rng.randint(0, 1))).isoformat(),
                "promised_delivery_date": (order_date + timedelta(days=promised_days)).isoformat(),
                "actual_delivery_date": (order_date + timedelta(days=actual_days)).isoformat(),
                "distance_miles": distance_miles,
                "shipping_cost": shipping_cost,
                "damage_flag": rng.random() < 0.025,
            }
        )
    return {"orders": orders, "shipments": shipments}


def write_table(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate(rows: int, seed: int, paths: LocalPaths) -> None:
    rng = random.Random(seed)
    dimensions = build_dimension_tables(rng)
    transactions = build_transactions(rng, dimensions, rows)
    for name, table_rows in {**dimensions, **transactions}.items():
        write_table(paths.raw_dir / f"{name}.csv", table_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SupplyFlow source files.")
    parser.add_argument("--rows", type=int, default=2500, help="Number of orders and shipments to create.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable demo data.")
    args = parser.parse_args()
    generate(args.rows, args.seed, LocalPaths())
    print(f"Generated {args.rows:,} SupplyFlow records in {LocalPaths().raw_dir}")


if __name__ == "__main__":
    main()
