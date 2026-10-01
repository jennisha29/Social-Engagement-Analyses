from __future__ import annotations

from pathlib import Path

import os

from azure.identity import AzureCliCredential, ClientSecretCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient

from tweetpulse.config import azure_config


def upload_file(path: Path, blob_prefix: str = "raw") -> None:
    config = azure_config()
    if config.tenant_id and config.client_id and config.client_secret:
        credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )
    elif (
        os.getenv("IDENTITY_ENDPOINT")
        or os.getenv("MSI_ENDPOINT")
        or os.getenv("WEBSITE_SITE_NAME")
        or os.getenv("FUNCTIONS_WORKER_RUNTIME")
    ):
        credential = ManagedIdentityCredential()
    else:
        credential = AzureCliCredential()
    account_url = f"https://{config.storage_account}.blob.core.windows.net"
    service_client = BlobServiceClient(account_url=account_url, credential=credential)
    blob_client = service_client.get_blob_client(
        container=config.container,
        blob=f"{blob_prefix}/{path.name}",
    )
    with path.open("rb") as file:
        blob_client.upload_blob(file, overwrite=True)
