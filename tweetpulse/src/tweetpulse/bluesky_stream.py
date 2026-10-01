from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import websockets

from tweetpulse.blob_storage import upload_file
from tweetpulse.config import LOCAL_BLOB_DIR


DEFAULT_JETSTREAM_URL = (
    "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"
)
POSITIVE_WORDS = {
    "amazing",
    "best",
    "excited",
    "good",
    "great",
    "happy",
    "improve",
    "love",
    "nice",
    "win",
}
NEGATIVE_WORDS = {
    "angry",
    "bad",
    "broken",
    "fail",
    "hate",
    "issue",
    "loss",
    "sad",
    "terrible",
    "worse",
}
TOPIC_KEYWORDS = {
    "ai": {"ai", "artificial intelligence", "chatgpt", "llm", "model", "openai"},
    "cloud": {"azure", "aws", "cloud", "snowflake", "databricks"},
    "data": {"analytics", "data", "database", "pipeline", "sql"},
    "mlops": {"deploy", "deployment", "mlops", "monitoring", "production"},
    "security": {"breach", "privacy", "security", "vulnerability"},
}


def classify_topic(text: str) -> str:
    lowered = text.lower()
    scores = {
        topic: sum(1 for keyword in keywords if keyword in lowered)
        for topic, keywords in TOPIC_KEYWORDS.items()
    }
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else "general"


def classify_sentiment(text: str) -> str:
    words = set(re.findall(r"[a-z']+", text.lower()))
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def hashtags(text: str, topic: str) -> list[str]:
    tags = [value.lower() for value in re.findall(r"#([A-Za-z0-9_]+)", text)]
    if topic not in tags:
        tags.insert(0, topic)
    return tags[:5]


def stable_engagement(*values: str) -> tuple[int, int, int]:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()
    likes = int(digest[:4], 16) % 900
    replies = int(digest[4:8], 16) % 120
    reposts = int(digest[8:12], 16) % 250
    return likes, replies, reposts


def created_at(record: dict[str, Any], fallback_time_us: int | None) -> str:
    value = record.get("createdAt")
    if isinstance(value, str):
        return value
    if fallback_time_us:
        return datetime.fromtimestamp(fallback_time_us / 1_000_000, tz=UTC).isoformat()
    return datetime.now(UTC).isoformat()


def jetstream_message_to_event(message: str) -> dict[str, object] | None:
    payload = json.loads(message)
    if payload.get("kind") != "commit":
        return None

    commit = payload.get("commit")
    if not isinstance(commit, dict):
        return None
    if commit.get("operation") != "create":
        return None
    if commit.get("collection") != "app.bsky.feed.post":
        return None

    record = commit.get("record")
    if not isinstance(record, dict):
        return None

    text = str(record.get("text") or "").strip()
    if not text:
        return None

    repo = str(payload.get("did") or "unknown")
    rkey = str(commit.get("rkey") or "")
    cid = str(commit.get("cid") or "")
    post_uri = f"at://{repo}/app.bsky.feed.post/{rkey}" if rkey else ""
    topic = classify_topic(text)
    sentiment = classify_sentiment(text)
    likes, replies, reposts = stable_engagement(repo, rkey, cid, text)

    return {
        "tweet_id": hashlib.sha256(f"{repo}|{rkey}|{cid}".encode("utf-8")).hexdigest(),
        "author": repo,
        "text": text[:280],
        "topic": topic,
        "hashtags": hashtags(text, topic),
        "sentiment": sentiment,
        "likes": likes,
        "replies": replies,
        "reposts": reposts,
        "engagement": likes + replies + reposts,
        "created_at": created_at(record, payload.get("time_us")),
        "source_url": post_uri,
        "source_type": "bluesky_jetstream",
    }


def write_batch(rows: list[dict[str, object]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_path = output_dir / f"bluesky_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.jsonl"
    with batch_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")
    return batch_path


async def collect_posts(
    url: str,
    output_dir: Path,
    batch_size: int,
    max_posts: int,
    upload_azure: bool,
) -> None:
    rows: list[dict[str, object]] = []
    total = 0
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as websocket:
        async for message in websocket:
            event = jetstream_message_to_event(message)
            if event is None:
                continue
            rows.append(event)
            total += 1

            if len(rows) >= batch_size:
                batch_path = write_batch(rows, output_dir)
                if upload_azure:
                    upload_file(batch_path)
                print(f"Wrote {len(rows)} Bluesky posts to {batch_path}")
                rows = []

            if total >= max_posts:
                break

    if rows:
        batch_path = write_batch(rows, output_dir)
        if upload_azure:
            upload_file(batch_path)
        print(f"Wrote {len(rows)} Bluesky posts to {batch_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream public Bluesky posts into TweetPulse JSONL batches.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-posts", type=int, default=500)
    parser.add_argument("--output-dir", type=Path, default=LOCAL_BLOB_DIR)
    parser.add_argument("--url", default=os.getenv("BLUESKY_JETSTREAM_URL", DEFAULT_JETSTREAM_URL))
    parser.add_argument("--upload-azure", action="store_true")
    args = parser.parse_args()

    asyncio.run(
        collect_posts(
            url=args.url,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            max_posts=args.max_posts,
            upload_azure=args.upload_azure,
        )
    )


if __name__ == "__main__":
    main()
