# TweetPulse Automation With Azure Functions

TweetPulse can run ingestion automatically with an Azure Functions Timer Trigger. The timer wrapper is defined in `function_app.py`.

## Schedule

The timer uses this CRON expression:

```text
0 */30 * * * *
```

That means:

```text
Every 30 minutes
```

Each run collects a bounded batch:

```text
BLUESKY_MAX_POSTS=500
BLUESKY_BATCH_SIZE=100
```

So every 30 minutes it writes and uploads five JSONL files of 100 posts each.

## Required App Settings

Set these on the Azure Function App:

```text
AZURE_STORAGE_ACCOUNT=tweetpulsejp260621
AZURE_STORAGE_CONTAINER=tweetpulse-raw
BLUESKY_MAX_POSTS=500
BLUESKY_BATCH_SIZE=100
BLUESKY_JETSTREAM_URL=wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post
```

The Function App also needs `AzureWebJobsStorage`, which Azure Functions uses for timer state and runtime storage.

## Identity

Enable a system-assigned managed identity on the Function App, then grant that identity:

```text
Storage Blob Data Contributor
```

Scope:

```text
/subscriptions/bd43048f-3a41-4143-8390-711219b36c93/resourceGroups/rg-tweetpulse-personal/providers/Microsoft.Storage/storageAccounts/tweetpulsejp260621
```

## Local Test

Install dependencies:

```bash
cd /Users/jennishachristinamartin/Desktop/tweetpulse
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run the same ingestion manually:

```bash
python -m tweetpulse.bluesky_stream --max-posts 500 --batch-size 100 --upload-azure
```

## Deployment Notes

Deploying the Function App is the next cloud step. It can use the Azure Functions Consumption plan, which is low-cost for small scheduled jobs, but it is still a billable Azure resource after free grants/credits. Keep `BLUESKY_MAX_POSTS` bounded to avoid accidental high-volume ingestion.
