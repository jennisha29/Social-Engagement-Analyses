from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
MARTS_DIR = DATA_DIR / "marts"
WAREHOUSE_DIR = DATA_DIR / "warehouse"


@dataclass(frozen=True)
class LocalPaths:
    raw_dir: Path = RAW_DIR
    curated_dir: Path = CURATED_DIR
    marts_dir: Path = MARTS_DIR
    warehouse_dir: Path = WAREHOUSE_DIR

    @property
    def orders_path(self) -> Path:
        return self.raw_dir / "orders.csv"

    @property
    def shipments_path(self) -> Path:
        return self.raw_dir / "shipments.csv"

    @property
    def carriers_path(self) -> Path:
        return self.raw_dir / "carriers.csv"

    @property
    def customers_path(self) -> Path:
        return self.raw_dir / "customers.csv"

    @property
    def products_path(self) -> Path:
        return self.raw_dir / "products.csv"

    @property
    def locations_path(self) -> Path:
        return self.raw_dir / "locations.csv"

    @property
    def facts_path(self) -> Path:
        return self.marts_dir / "fact_shipments.csv"

    @property
    def warehouse_fact_path(self) -> Path:
        return self.warehouse_dir / "fact_shipments.csv"
