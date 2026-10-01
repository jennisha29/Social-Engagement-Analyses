# Azure CLI Steps

Replace values in angle brackets before running these commands.

```bash
az login
az group create --name rg-tweetpulse --location eastus
az provider register --namespace Microsoft.EventGrid

az storage account create \
  --resource-group rg-tweetpulse \
  --name <blob_storage_account> \
  --sku Standard_LRS \
  --location eastus \
  --kind StorageV2

az storage container create \
  --account-name <blob_storage_account> \
  --name tweetpulse-raw \
  --auth-mode login

az storage account create \
  --resource-group rg-tweetpulse \
  --name <queue_storage_account> \
  --sku Standard_LRS \
  --location eastus \
  --kind StorageV2

az storage queue create \
  --account-name <queue_storage_account> \
  --name tweetpulse-snowpipe-events \
  --auth-mode login
```

After Snowflake creates the notification integration, run `desc integration tweetpulse_azure_queue_int;` and use the Azure consent URL and app name it returns. Then create the Event Grid subscription that sends `Microsoft.Storage.BlobCreated` events to the storage queue.

```bash
az eventgrid event-subscription create \
  --name tweetpulse-blob-created \
  --source-resource-id /subscriptions/<subscription_id>/resourceGroups/rg-tweetpulse/providers/Microsoft.Storage/storageAccounts/<blob_storage_account> \
  --endpoint-type storagequeue \
  --endpoint /subscriptions/<subscription_id>/resourceGroups/rg-tweetpulse/providers/Microsoft.Storage/storageAccounts/<queue_storage_account>/queueservices/default/queues/tweetpulse-snowpipe-events \
  --included-event-types Microsoft.Storage.BlobCreated
```
