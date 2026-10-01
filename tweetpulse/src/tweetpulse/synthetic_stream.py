from __future__ import annotations

import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tweetpulse.config import LOCAL_BLOB_DIR


TOPICS = ["ai", "mlops", "snowflake", "azure", "python", "datapipeline", "analytics"]
SENTIMENTS = ["positive", "neutral", "negative"]
AUTHORS = ["data_mia", "cloud_raj", "ops_lee", "ml_ana", "sql_taylor"]
TEMPLATES = [
    "Shipping a new {topic} workflow today",
    "{topic} is moving fast and the dashboards are finally useful",
    "Debugging {topic} latency before the standup",
    "Fresh notes on {topic} architecture and production tradeoffs",
    "The {topic} metrics are telling a very different story now",
]


def build_tweet() -> dict[str, object]:
    topic = random.choice(TOPICS)
    likes = random.randint(0, 900)
    replies = random.randint(0, 120)
    reposts = random.randint(0, 250)
    return {
        "tweet_id": str(uuid4()),
        "author": random.choice(AUTHORS),
        "text": random.choice(TEMPLATES).format(topic=topic),
        "topic": topic,
        "hashtags": [topic, random.choice(TOPICS)],
        "sentiment": random.choices(SENTIMENTS, weights=[0.5, 0.35, 0.15], k=1)[0],
        "likes": likes,
        "replies": replies,
        "reposts": reposts,
        "engagement": likes + replies + reposts,
        "created_at": datetime.now(UTC).isoformat(),
    }


def write_batch(output_dir: Path, batch_size: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_path = output_dir / f"tweets_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}.jsonl"
    with batch_path.open("w", encoding="utf-8") as file:
        for _ in range(batch_size):
            file.write(json.dumps(build_tweet()) + "\n")
    return batch_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local tweet batches for TweetPulse.")
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    for _ in range(args.batches):
        batch_path = write_batch(LOCAL_BLOB_DIR, args.batch_size)
        print(f"Wrote {batch_path}")
        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
