from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from meta_api_common import get_json, load_env, paginate, utc_now, write_outputs


DEFAULT_MEDIA_FIELDS = ",".join(
    [
        "id",
        "caption",
        "media_type",
        "media_url",
        "permalink",
        "timestamp",
        "like_count",
        "comments_count",
    ]
)
DEFAULT_INSIGHT_METRICS = ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions"]


def insight_value(item: dict[str, Any]) -> str:
    values = item.get("values", [])
    if isinstance(values, list) and values:
        value = values[0].get("value")
        return "" if value is None else str(value)
    value = item.get("value")
    return "" if value is None else str(value)


def fetch_insights(media_id: str, metrics: list[str], *, token: str, graph_base: str) -> tuple[dict[str, str], dict[str, Any]]:
    endpoint = f"{graph_base}/{media_id}/insights"
    params = {"metric": ",".join(metrics), "access_token": token}
    try:
        payload = get_json(endpoint, params)
    except Exception as error:
        payload = {"error": str(error), "fallback": []}
        merged: dict[str, str] = {}
        for metric in metrics:
            try:
                one = get_json(endpoint, {"metric": metric, "access_token": token})
                payload["fallback"].append(one)
                for item in one.get("data", []):
                    if isinstance(item, dict) and item.get("name"):
                        merged[item["name"]] = insight_value(item)
            except Exception as metric_error:
                payload["fallback"].append({"metric": metric, "error": str(metric_error)})
        return merged, payload

    merged = {}
    for item in payload.get("data", []):
        if isinstance(item, dict) and item.get("name"):
            merged[item["name"]] = insight_value(item)
    return merged, payload


def normalize_media(media: dict[str, Any], insights: dict[str, str]) -> dict[str, str]:
    return {
        "platform": "instagram",
        "author_handle": "goodsuniteus",
        "post_url": str(media.get("permalink", "")),
        "post_id": str(media.get("id", "")),
        "threads_internal_id": "",
        "published_at": str(media.get("timestamp", "")),
        "post_text": str(media.get("caption", "")),
        "likes": insights.get("likes") or str(media.get("like_count", "")),
        "comments": insights.get("comments") or str(media.get("comments_count", "")),
        "replies": "",
        "shares": insights.get("shares", ""),
        "reposts": "",
        "quotes": "",
        "views": insights.get("views", ""),
        "reach": insights.get("reach", ""),
        "saved": insights.get("saved", ""),
        "total_interactions": insights.get("total_interactions", ""),
        "image_url": str(media.get("media_url", "")),
        "media_type": str(media.get("media_type", "")).lower(),
        "scraped_at": utc_now(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch owned Instagram media and post insights via Meta Graph API.")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).with_name(".env"))
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/meta_api"))
    parser.add_argument("--prefix", default="meta_instagram_posts")
    parser.add_argument("--api-version", default="v23.0")
    parser.add_argument("--instagram-user-id", default=os.getenv("INSTAGRAM_USER_ID", ""))
    parser.add_argument("--access-token", default=os.getenv("META_ACCESS_TOKEN", ""))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--media-fields", default=DEFAULT_MEDIA_FIELDS)
    parser.add_argument("--insight-metrics", default=",".join(DEFAULT_INSIGHT_METRICS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)
    token = args.access_token or os.getenv("META_ACCESS_TOKEN", "")
    instagram_user_id = args.instagram_user_id or os.getenv("INSTAGRAM_USER_ID", "")
    if not token:
        raise SystemExit("Set META_ACCESS_TOKEN in decodo_travel_scraper/.env or pass --access-token.")
    if not instagram_user_id:
        raise SystemExit("Set INSTAGRAM_USER_ID in decodo_travel_scraper/.env or pass --instagram-user-id.")

    graph_base = f"https://graph.facebook.com/{args.api_version}"
    media_endpoint = f"{graph_base}/{instagram_user_id}/media"
    media_rows = paginate(
        media_endpoint,
        {"fields": args.media_fields, "limit": "100", "access_token": token},
        limit=args.limit,
    )
    metrics = [metric.strip() for metric in args.insight_metrics.split(",") if metric.strip()]

    normalized: list[dict[str, str]] = []
    raw_rows: list[dict[str, Any]] = []
    for media in media_rows:
        media_id = str(media.get("id", ""))
        insights, raw_insights = fetch_insights(media_id, metrics, token=token, graph_base=graph_base)
        normalized.append(normalize_media(media, insights))
        raw_rows.append({"media": media, "insights": raw_insights})
        print(f"Fetched Instagram media {media_id}")

    write_outputs(normalized, raw_rows, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
