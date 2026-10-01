# Next Steps: Finish Cross-Platform Collection

Bluesky author-feed collection is complete for this run.

## Completed

- `bluesky_20260929T203917Z.csv`
- `bluesky_20260929T203917Z.jsonl`
- `bluesky_public_audit_summary.md`

## Blocked By Missing Credentials

Set these environment variables, then rerun the commands.

### X / Twitter

Required:

```bash
export X_BEARER_TOKEN="..."
```

Run:

```bash
PYTHONPATH=tweetpulse/src python3 -m tweetpulse.social_audit_collectors \
  --platform x \
  --x-username goodsuniteus \
  --max-posts 250 \
  --output-dir tweetpulse/data/social_audit/run_20260929
```

### Instagram

Required:

```bash
export INSTAGRAM_USER_ID="..."
export INSTAGRAM_ACCESS_TOKEN="..."
```

Run:

```bash
PYTHONPATH=tweetpulse/src python3 -m tweetpulse.social_audit_collectors \
  --platform instagram \
  --max-posts 250 \
  --output-dir tweetpulse/data/social_audit/run_20260929
```

### Threads

Required:

```bash
export THREADS_ACCESS_TOKEN="..."
```

Run:

```bash
PYTHONPATH=tweetpulse/src python3 -m tweetpulse.social_audit_collectors \
  --platform threads \
  --max-posts 250 \
  --output-dir tweetpulse/data/social_audit/run_20260929
```

### Decodo

Required:

```bash
export DECODO_USERNAME="..."
export DECODO_PASSWORD="..."
```

Or:

```bash
export DECODO_AUTH="..."
```

Run for allowed public pages:

```bash
PYTHONPATH=tweetpulse/src python3 -m tweetpulse.decodo_scraper \
  --url-file travel_urls.txt \
  --prefix travel_pages \
  --output-dir tweetpulse/data/decodo
```

## Note

The Bluesky mention-search endpoint returned HTTP 403 from the public API during this run. The author-feed endpoint worked successfully.
