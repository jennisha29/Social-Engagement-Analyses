from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_BLOB_DIR = PROJECT_ROOT / "data" / "blob" / "raw"


@dataclass(frozen=True)
class AzureConfig:
    storage_account: str
    container: str
    tenant_id: str
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    password: str
    authenticator: str
    role: str
    warehouse: str
    database: str
    schema: str


def dashboard_mode() -> str:
    return os.getenv("DASHBOARD_MODE", "local").strip().lower()


def azure_config() -> AzureConfig:
    return AzureConfig(
        storage_account=os.getenv("AZURE_STORAGE_ACCOUNT", ""),
        container=os.getenv("AZURE_STORAGE_CONTAINER", "tweetpulse-raw"),
        tenant_id=os.getenv("AZURE_TENANT_ID", ""),
        client_id=os.getenv("AZURE_CLIENT_ID", ""),
        client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
    )


def snowflake_config() -> SnowflakeConfig:
    return SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
        user=os.getenv("SNOWFLAKE_USER", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        authenticator=os.getenv("SNOWFLAKE_AUTHENTICATOR", "snowflake"),
        role=os.getenv("SNOWFLAKE_ROLE", "TWEETPULSE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "TWEETPULSE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "TWEETPULSE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "ANALYTICS"),
    )
