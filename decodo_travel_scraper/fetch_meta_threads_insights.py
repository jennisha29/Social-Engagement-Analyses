from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from meta_api_common import get_json, load_env, paginate, utc_now, write_outputs


DEFAULT_THREAD_FIELDS = ",".join(
    [
        "id",
        "media_type",
        "media_url",
        "permalink",
        "owner",
        "username",
        "text",
        "timestamp",
        "shortcode",
        "thumbnail_url",
    ]
)
DEFAULT_INSIGHT_METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]


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


def normalize_thread(post: dict[str, Any], insights: dict[str, str]) -> dict[str, str]:
    image_url = str(post.get("media_url") or post.get("thumbnail_url") or "")
    return {
        "platform": "threads",
        "author_handle": str(post.get("username", "goodsuniteus")),
        "post_url": str(post.get("permalink", "")),
        "post_id": str(post.get("shortcode") or post.get("id", "")),
        "threads_internal_id": str(post.get("id", "")),
        "published_at": str(post.get("timestamp", "")),
        "post_text": str(post.get("text", "")),
        "likes": insights.get("likes", ""),
        "comments": "",
        "replies": insights.get("replies", ""),
        "shares": insights.get("shares", ""),
        "reposts": insights.get("reposts", ""),
        "quotes": insights.get("quotes", ""),
        "views": insights.get("views", ""),
        "reach": "",
        "saved": "",
        "total_interactions": "",
        "image_url": image_url,
        "media_type": str(post.get("media_type", "")).lower(),
        "scraped_at": utc_now(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch owned Threads posts and post insights via Threads API.")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).with_name(".env"))
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/meta_api"))
    parser.add_argument("--prefix", default="meta_threads_posts")
    parser.add_argument("--api-version", default="v1.0")
    parser.add_argument("--api-host", default="https://graph.threads.net")
    parser.add_argument("--threads-user-id", default=os.getenv("THREADS_USER_ID", ""))
    parser.add_argument("--access-token", default=os.getenv("THREADS_ACCESS_TOKEN", ""))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--post-fields", default=DEFAULT_THREAD_FIELDS)
    parser.add_argument("--insight-metrics", default=",".join(DEFAULT_INSIGHT_METRICS))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)
    token = args.access_token or os.getenv("THREADS_ACCESS_TOKEN", "") or os.getenv("META_ACCESS_TOKEN", "")
    threads_user_id = args.threads_user_id or os.getenv("THREADS_USER_ID", "")
    if not token:
        raise SystemExit("Set THREADS_ACCESS_TOKEN or META_ACCESS_TOKEN in decodo_travel_scraper/.env, or pass --access-token.")
    if not threads_user_id:
        raise SystemExit("Set THREADS_USER_ID in decodo_travel_scraper/.env or pass --threads-user-id.")

    graph_base = f"{args.api_host.rstrip('/')}/{args.api_version}"
    posts_endpoint = f"{graph_base}/{threads_user_id}/threads"
    posts = paginate(
        posts_endpoint,
        {"fields": args.post_fields, "limit": "100", "access_token": token},
        limit=args.limit,
    )
    metrics = [metric.strip() for metric in args.insight_metrics.split(",") if metric.strip()]

    normalized: list[dict[str, str]] = []
    raw_rows: list[dict[str, Any]] = []
    for post in posts:
        post_id = str(post.get("id", ""))
        insights, raw_insights = fetch_insights(post_id, metrics, token=token, graph_base=graph_base)
        normalized.append(normalize_thread(post, insights))
        raw_rows.append({"post": post, "insights": raw_insights})
        print(f"Fetched Threads post {post_id}")

    write_outputs(normalized, raw_rows, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
