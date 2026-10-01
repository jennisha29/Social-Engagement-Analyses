from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from tweetpulse.config import LOCAL_BLOB_DIR


DEFAULT_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://www.theverge.com/rss/index.xml",
]
POSITIVE_WORDS = {
    "advance",
    "benefit",
    "breakthrough",
    "gain",
    "growth",
    "improve",
    "launch",
    "positive",
    "success",
    "win",
}
NEGATIVE_WORDS = {
    "ban",
    "breach",
    "concern",
    "crash",
    "decline",
    "delay",
    "fail",
    "loss",
    "negative",
    "risk",
}
TOPIC_KEYWORDS = {
    "ai": {"ai", "artificial intelligence", "model", "openai", "llm"},
    "cloud": {"azure", "aws", "cloud", "snowflake", "databricks"},
    "security": {"breach", "security", "privacy", "vulnerability"},
    "data": {"data", "analytics", "pipeline", "database"},
    "business": {"market", "startup", "company", "revenue"},
}


def fetch_feed(url: str, timeout: int = 15) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TweetPulseStudentProject/0.1 (+respectful RSS ingestion)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def strip_markup(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def child_text(element: ET.Element, names: list[str]) -> str:
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def parse_datetime(value: str) -> str:
    if not value:
        return datetime.now(UTC).isoformat()
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        return datetime.now(UTC).isoformat()


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


def stable_engagement(*values: str) -> tuple[int, int, int]:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()
    likes = int(digest[:4], 16) % 900
    replies = int(digest[4:8], 16) % 120
    reposts = int(digest[8:12], 16) % 250
    return likes, replies, reposts


def parse_items(feed_url: str, payload: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(payload)
    source_host = urllib.parse.urlparse(feed_url).netloc
    items = root.findall(".//item")
    if not items:
        items = root.findall("{http://www.w3.org/2005/Atom}entry")

    rows: list[dict[str, object]] = []
    for item in items:
        title = strip_markup(child_text(item, ["title", "{http://www.w3.org/2005/Atom}title"]))
        description = strip_markup(
            child_text(
                item,
                [
                    "description",
                    "summary",
                    "{http://www.w3.org/2005/Atom}summary",
                    "{http://www.w3.org/2005/Atom}content",
                ],
            )
        )
        link = child_text(item, ["link"])
        if not link:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            link = atom_link.attrib.get("href", "") if atom_link is not None else ""

        published = child_text(
            item,
            ["pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}updated"],
        )
        text = f"{title}. {description}".strip()
        topic = classify_topic(text)
        sentiment = classify_sentiment(text)
        likes, replies, reposts = stable_engagement(title, link, published)
        tweet_id = hashlib.sha256(f"{feed_url}|{link}|{title}".encode("utf-8")).hexdigest()
        rows.append(
            {
                "tweet_id": tweet_id,
                "author": source_host,
                "text": text[:280],
                "topic": topic,
                "hashtags": [topic, "rss"],
                "sentiment": sentiment,
                "likes": likes,
                "replies": replies,
                "reposts": reposts,
                "engagement": likes + replies + reposts,
                "created_at": parse_datetime(published),
                "source_url": link or feed_url,
                "source_type": "rss",
            }
        )
    return rows


def write_batch(rows: list[dict[str, object]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_path = output_dir / f"rss_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.jsonl"
    with batch_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")
    return batch_path


def feed_urls() -> list[str]:
    configured = os.getenv("RSS_FEED_URLS", "").strip()
    if not configured:
        return DEFAULT_FEEDS
    return [url.strip() for url in configured.split(",") if url.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public RSS feeds into TweetPulse JSONL batches.")
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, default=LOCAL_BLOB_DIR)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for url in feed_urls():
        try:
            rows.extend(parse_items(url, fetch_feed(url)))
            time.sleep(args.sleep_seconds)
        except (ET.ParseError, TimeoutError, urllib.error.URLError) as error:
            print(f"Skipped {url}: {error}")

    if not rows:
        raise SystemExit("No RSS items were collected.")

    batch_path = write_batch(rows, args.output_dir)
    print(f"Wrote {len(rows)} RSS items to {batch_path}")


if __name__ == "__main__":
    main()
