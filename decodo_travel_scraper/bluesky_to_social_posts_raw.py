from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path


def media_type_from_raw(raw: dict) -> tuple[str, str]:
    embed = raw.get("embed") or raw.get("record", {}).get("embed") or {}
    embed_type = embed.get("$type", "")
    if "images" in embed_type:
        images = embed.get("images", [])
        image_url = ""
        if images and isinstance(images[0], dict):
            image_url = images[0].get("fullsize", "") or images[0].get("thumb", "")
        return "image", image_url
    if "video" in embed_type:
        return "video", embed.get("thumbnail", "")
    if "external" in embed_type:
        return "external_link", ""
    return "text", ""


def parse_raw(raw_value: str) -> dict:
    try:
        return json.loads(raw_value)
    except Exception:
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert normalized Bluesky API CSV to social_posts_raw schema.")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-csv", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = list(csv.DictReader(args.input_csv.open(encoding="utf-8")))
    output = args.output_csv or args.input_csv.with_name("social_posts_raw.csv")
    scraped_at = datetime.now(UTC).isoformat()

    fields = [
        "platform",
        "post_url",
        "post_id",
        "published_at",
        "post_text",
        "likes",
        "comments",
        "replies",
        "shares",
        "reposts",
        "quotes",
        "image_url",
        "media_type",
        "scraped_at",
    ]

    converted = []
    for row in rows:
        raw = parse_raw(row.get("raw", ""))
        media_type, image_url = media_type_from_raw(raw)
        converted.append(
            {
                "platform": row.get("platform", "bluesky"),
                "post_url": row.get("post_url", ""),
                "post_id": row.get("post_id", "").rsplit("/", 1)[-1],
                "published_at": row.get("published_at", ""),
                "post_text": row.get("text", ""),
                "likes": row.get("likes", ""),
                "comments": row.get("comments", ""),
                "replies": row.get("replies", ""),
                "shares": row.get("shares", ""),
                "reposts": row.get("reposts", ""),
                "quotes": row.get("quotes", ""),
                "image_url": image_url,
                "media_type": media_type,
                "scraped_at": scraped_at,
            }
        )

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(converted)

    print(f"Wrote {len(converted)} rows to {output}")


if __name__ == "__main__":
    main()
