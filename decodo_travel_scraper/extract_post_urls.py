from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin


SOCIAL_PATTERNS = {
    "instagram": [
        r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+/?",
        r"/(?:p|reel|tv)/[A-Za-z0-9_-]+/?",
    ],
    "threads": [
        r"https?://(?:www\.)?threads\.(?:com|net)/@[^/\s\"']+/post/[A-Za-z0-9_-]+/?",
        r"/@[^/\s\"']+/post/[A-Za-z0-9_-]+/?",
    ],
    "x": [
        r"https?://(?:www\.)?(?:x|twitter)\.com/goodsuniteus/status/\d+",
        r"/goodsuniteus/status/\d+",
    ],
    "bluesky": [
        r"https?://bsky\.app/profile/goodsuniteus\.bsky\.social/post/[A-Za-z0-9_-]+",
        r"/profile/goodsuniteus\.bsky\.social/post/[A-Za-z0-9_-]+",
    ],
}


BASE_URLS = {
    "instagram": "https://www.instagram.com",
    "threads": "https://www.threads.com",
    "x": "https://x.com",
    "bluesky": "https://bsky.app",
}


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def normalize_url(platform: str, value: str) -> str:
    value = html.unescape(value).strip().rstrip(')"\',.')
    if value.startswith("http"):
        value = value.replace("https://twitter.com/", "https://x.com/")
        return value.rstrip("/")
    return urljoin(BASE_URLS[platform], value).rstrip("/")


def post_id(platform: str, url: str) -> str:
    if platform == "x":
        return url.rstrip("/").rsplit("/", 1)[-1]
    if platform in {"instagram", "threads", "bluesky"}:
        return url.rstrip("/").rsplit("/", 1)[-1]
    return ""


def extract_from_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for platform, patterns in SOCIAL_PATTERNS.items():
        for pattern in patterns:
            for found in re.findall(pattern, text, flags=re.I):
                url = normalize_url(platform, found)
                rows.append(
                    {
                        "platform": platform,
                        "post_url": url,
                        "post_id": post_id(platform, url),
                    }
                )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract individual social post URLs from Decodo JSONL.")
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output-csv", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []

    for line in args.jsonl.open(encoding="utf-8"):
        payload = json.loads(line)
        text = "\n".join(iter_strings(payload))
        for row in extract_from_text(text):
            key = (row["platform"], row["post_url"])
            if key not in seen:
                seen.add(key)
                rows.append(row)

    output_csv = args.output_csv or args.jsonl.with_name(args.jsonl.stem + "_post_urls.csv")
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["platform", "post_url", "post_id"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} post URLs to {output_csv}")


if __name__ == "__main__":
    main()
