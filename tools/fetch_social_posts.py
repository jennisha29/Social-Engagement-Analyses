#!/usr/bin/env python3
"""
Fetch owned social post metadata + analytics into one normalized file.

Supported inputs:
  - Instagram Graph API media + media insights
  - Threads API posts + post insights
  - Bluesky public API author feed
  - X API v2 user posts
  - TikTok Business API best-effort video list, or TikTok Business Suite CSV import

Examples:
  export META_ACCESS_TOKEN="..."
  export IG_USER_ID="1784..."
  python tools/fetch_social_posts.py --platform instagram --days 90 --out social_posts.jsonl

  export THREADS_ACCESS_TOKEN="..."
  python tools/fetch_social_posts.py --platform threads --limit 100 --out social_posts.jsonl

  python tools/fetch_social_posts.py --platform bluesky --bluesky-handle goodsuniteus.bsky.social

  export X_BEARER_TOKEN="..."
  export X_USER_ID="123456"
  python tools/fetch_social_posts.py --platform x --days 90

  python tools/fetch_social_posts.py --platform tiktok_csv --tiktok-csv ~/Downloads/tiktok_analytics.csv

Output columns/schema are intentionally stable and LLM-friendly:
  platform, post_id, post_url, created_at, text, media_type, metrics, raw, fetched_at
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUT = "social_posts.jsonl"


@dataclass
class SocialPost:
    platform: str
    post_id: str
    post_url: str | None
    created_at: str | None
    text: str | None
    media_type: str | None
    metrics: dict[str, Any]
    raw: dict[str, Any]
    fetched_at: str


class ApiError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cutoff_iso(days: int | None) -> str | None:
    if not days:
        return None
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def is_after_cutoff(value: str | None, cutoff: str | None) -> bool:
    if not cutoff:
        return True
    left = parse_iso(value)
    right = parse_iso(cutoff)
    if not left or not right:
        return True
    return left >= right


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ApiError(f"Missing required environment variable: {name}")
    return value


def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request_url = url
            if params:
                separator = "&" if "?" in request_url else "?"
                request_url = f"{request_url}{separator}{urllib.parse.urlencode(params)}"

            body = None
            request_headers = dict(headers or {})
            if json_body is not None:
                body = json.dumps(json_body).encode("utf-8")
                request_headers["Content-Type"] = "application/json"

            request = urllib.request.Request(
                request_url,
                data=body,
                headers=request_headers,
                method=method,
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise ApiError(f"{exc.code} {url}: {message[:1000]}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
    raise ApiError(str(last_error))


def graph_get(path_or_url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        version = os.getenv("META_GRAPH_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{version}/{path_or_url.lstrip('/')}"
    query = dict(params or {})
    query["access_token"] = token
    return request_json("GET", url, params=query)


def threads_get(path_or_url: str, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        version = os.getenv("THREADS_API_VERSION", "v1.0")
        url = f"https://graph.threads.net/{version}/{path_or_url.lstrip('/')}"
    query = dict(params or {})
    query["access_token"] = token
    return request_json("GET", url, params=query)


def paged_data(
    first: dict[str, Any],
    token: str,
    get_fn,
    *,
    max_pages: int = 25,
) -> Iterable[dict[str, Any]]:
    page = first
    pages = 0
    while page and pages < max_pages:
        for item in page.get("data", []):
            yield item
        next_url = page.get("paging", {}).get("next")
        if not next_url:
            break
        page = get_fn(next_url, token)
        pages += 1


def insights_to_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for row in payload.get("data", []):
        name = row.get("name")
        values = row.get("values") or []
        if not name or not values:
            continue
        if len(values) == 1:
            metrics[name] = values[0].get("value")
        else:
            metrics[name] = [value.get("value") for value in values]
    return metrics


def fetch_instagram(limit: int, days: int | None) -> list[SocialPost]:
    token = require_env("META_ACCESS_TOKEN")
    ig_user_id = require_env("IG_USER_ID")
    cutoff = cutoff_iso(days)
    fetched_at = utc_now()

    media_fields = ",".join(
        [
            "id",
            "caption",
            "media_type",
            "media_product_type",
            "permalink",
            "timestamp",
            "like_count",
            "comments_count",
            "thumbnail_url",
            "media_url",
        ]
    )
    first = graph_get(
        f"{ig_user_id}/media",
        token,
        {"fields": media_fields, "limit": min(limit, 100)},
    )

    insight_candidates = [
        "views",
        "reach",
        "likes",
        "comments",
        "saved",
        "shares",
        "total_interactions",
        "follows",
        "profile_visits",
        "profile_activity",
        "ig_reels_avg_watch_time",
        "ig_reels_video_view_total_time",
    ]

    posts: list[SocialPost] = []
    for media in paged_data(first, token, graph_get):
        if len(posts) >= limit:
            break
        if not is_after_cutoff(media.get("timestamp"), cutoff):
            continue

        metrics = {
            "like_count": media.get("like_count"),
            "comments_count": media.get("comments_count"),
        }

        media_id = media["id"]
        try:
            insights = graph_get(
                f"{media_id}/insights",
                token,
                {"metric": ",".join(insight_candidates)},
            )
            metrics.update(insights_to_metrics(insights))
        except ApiError:
            # Some insight metrics are media-type or permission dependent.
            for metric in insight_candidates:
                try:
                    insight = graph_get(f"{media_id}/insights", token, {"metric": metric})
                    metrics.update(insights_to_metrics(insight))
                except ApiError:
                    continue

        posts.append(
            SocialPost(
                platform="instagram",
                post_id=media_id,
                post_url=media.get("permalink"),
                created_at=media.get("timestamp"),
                text=media.get("caption"),
                media_type=media.get("media_product_type") or media.get("media_type"),
                metrics=metrics,
                raw=media,
                fetched_at=fetched_at,
            )
        )
    return posts


def fetch_threads(limit: int, days: int | None) -> list[SocialPost]:
    token = require_env("THREADS_ACCESS_TOKEN")
    cutoff = cutoff_iso(days)
    fetched_at = utc_now()

    fields = ",".join(
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
            "children",
            "is_quote_post",
        ]
    )
    first = threads_get("me/threads", token, {"fields": fields, "limit": min(limit, 100)})
    insight_metrics = ["views", "likes", "replies", "reposts", "quotes", "shares"]

    posts: list[SocialPost] = []
    for post in paged_data(first, token, threads_get):
        if len(posts) >= limit:
            break
        if not is_after_cutoff(post.get("timestamp"), cutoff):
            continue

        metrics: dict[str, Any] = {}
        try:
            insights = threads_get(
                f"{post['id']}/insights",
                token,
                {"metric": ",".join(insight_metrics)},
            )
            metrics.update(insights_to_metrics(insights))
        except ApiError:
            for metric in insight_metrics:
                try:
                    insight = threads_get(f"{post['id']}/insights", token, {"metric": metric})
                    metrics.update(insights_to_metrics(insight))
                except ApiError:
                    continue

        posts.append(
            SocialPost(
                platform="threads",
                post_id=post["id"],
                post_url=post.get("permalink"),
                created_at=post.get("timestamp"),
                text=post.get("text"),
                media_type=post.get("media_type"),
                metrics=metrics,
                raw=post,
                fetched_at=fetched_at,
            )
        )
    return posts


def bluesky_post_url(handle: str, uri: str) -> str:
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def fetch_bluesky(handle: str, limit: int, days: int | None, include_reposts: bool) -> list[SocialPost]:
    cutoff = cutoff_iso(days)
    fetched_at = utc_now()
    base = os.getenv("BLUESKY_API_BASE", "https://public.api.bsky.app")
    posts: list[SocialPost] = []
    cursor: str | None = None

    while len(posts) < limit:
        params = {"actor": handle, "limit": min(100, limit - len(posts))}
        if cursor:
            params["cursor"] = cursor
        payload = request_json(
            "GET",
            f"{base}/xrpc/app.bsky.feed.getAuthorFeed",
            params=params,
        )
        for item in payload.get("feed", []):
            if len(posts) >= limit:
                break
            if item.get("reason") and not include_reposts:
                continue

            post = item.get("post", {})
            record = post.get("record", {})
            created_at = record.get("createdAt") or post.get("indexedAt")
            if not is_after_cutoff(created_at, cutoff):
                continue

            embed = post.get("embed") or record.get("embed") or {}
            media_type = embed.get("$type")
            metrics = {
                "like_count": post.get("likeCount", 0),
                "reply_count": post.get("replyCount", 0),
                "repost_count": post.get("repostCount", 0),
                "quote_count": post.get("quoteCount", 0),
                "bookmark_count": post.get("bookmarkCount", 0),
            }
            posts.append(
                SocialPost(
                    platform="bluesky",
                    post_id=post.get("uri", ""),
                    post_url=bluesky_post_url(handle, post.get("uri", "")),
                    created_at=created_at,
                    text=record.get("text"),
                    media_type=media_type,
                    metrics=metrics,
                    raw=item,
                    fetched_at=fetched_at,
                )
            )

        cursor = payload.get("cursor")
        if not cursor:
            break

    return posts


def fetch_x(limit: int, days: int | None, include_private_metrics: bool) -> list[SocialPost]:
    token = require_env("X_BEARER_TOKEN")
    user_id = require_env("X_USER_ID")
    cutoff = cutoff_iso(days)
    fetched_at = utc_now()
    base = os.getenv("X_API_BASE", "https://api.x.com/2")

    tweet_fields = [
        "id",
        "text",
        "created_at",
        "public_metrics",
        "referenced_tweets",
        "attachments",
        "entities",
        "conversation_id",
        "lang",
    ]
    if include_private_metrics:
        tweet_fields.extend(["organic_metrics", "non_public_metrics", "promoted_metrics"])

    params: dict[str, Any] = {
        "max_results": min(max(limit, 5), 100),
        "tweet.fields": ",".join(tweet_fields),
        "expansions": "attachments.media_keys",
        "media.fields": "type,url,preview_image_url,public_metrics,alt_text,duration_ms",
    }
    if days:
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        params["start_time"] = start_time.isoformat(timespec="seconds").replace("+00:00", "Z")

    headers = {"Authorization": f"Bearer {token}"}
    posts: list[SocialPost] = []
    next_token: str | None = None

    while len(posts) < limit:
        if next_token:
            params["pagination_token"] = next_token
        payload = request_json(
            "GET",
            f"{base}/users/{user_id}/tweets",
            params=params,
            headers=headers,
        )
        media_by_key = {
            media.get("media_key"): media
            for media in payload.get("includes", {}).get("media", [])
            if media.get("media_key")
        }
        for tweet in payload.get("data", []):
            if len(posts) >= limit:
                break
            if not is_after_cutoff(tweet.get("created_at"), cutoff):
                continue
            media_keys = tweet.get("attachments", {}).get("media_keys", [])
            media = [media_by_key.get(key, {}) for key in media_keys]
            metrics = {}
            for key in ["public_metrics", "organic_metrics", "non_public_metrics", "promoted_metrics"]:
                if key in tweet:
                    metrics[key] = tweet[key]
            posts.append(
                SocialPost(
                    platform="x",
                    post_id=tweet["id"],
                    post_url=f"https://x.com/i/web/status/{tweet['id']}",
                    created_at=tweet.get("created_at"),
                    text=tweet.get("text"),
                    media_type=",".join(sorted({item.get("type", "") for item in media if item})),
                    metrics=metrics,
                    raw={"tweet": tweet, "media": media},
                    fetched_at=fetched_at,
                )
            )

        next_token = payload.get("meta", {}).get("next_token")
        if not next_token:
            break

    return posts


def fetch_tiktok_business(limit: int, days: int | None) -> list[SocialPost]:
    """
    Best-effort TikTok Business API fetcher.

    TikTok's organic/business account API access and exact account identifiers vary by app,
    region, and product approval. If this fails, use --platform tiktok_csv with an export
    from TikTok Web Business Suite Analytics.
    """
    token = require_env("TIKTOK_ACCESS_TOKEN")
    business_id = require_env("TIKTOK_BUSINESS_ID")
    fetched_at = utc_now()
    cutoff = cutoff_iso(days)
    url = os.getenv(
        "TIKTOK_VIDEO_LIST_URL",
        "https://business-api.tiktok.com/open_api/v1.3/business/video/list/",
    )
    headers = {"Access-Token": token}
    cursor = 0
    posts: list[SocialPost] = []

    while len(posts) < limit:
        params = {
            "business_id": business_id,
            "max_count": min(50, limit - len(posts)),
            "cursor": cursor,
        }
        payload = request_json("GET", url, params=params, headers=headers)
        data = payload.get("data", {})
        videos = data.get("videos") or data.get("list") or []
        for video in videos:
            created_at = video.get("create_time") or video.get("created_at")
            if isinstance(created_at, int):
                created_at = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
            if not is_after_cutoff(created_at, cutoff):
                continue
            metrics = {
                key: video.get(key)
                for key in [
                    "view_count",
                    "like_count",
                    "comment_count",
                    "share_count",
                    "play_count",
                    "reach",
                    "total_time_watched",
                    "average_watch_time",
                    "full_video_watched_rate",
                ]
                if key in video
            }
            posts.append(
                SocialPost(
                    platform="tiktok",
                    post_id=str(video.get("video_id") or video.get("item_id") or video.get("id")),
                    post_url=video.get("share_url") or video.get("video_url"),
                    created_at=created_at,
                    text=video.get("caption") or video.get("title"),
                    media_type="video",
                    metrics=metrics,
                    raw=video,
                    fetched_at=fetched_at,
                )
            )
        if not data.get("has_more"):
            break
        cursor = data.get("cursor") or data.get("next_cursor") or cursor + len(videos)
    return posts


def import_tiktok_csv(path: Path) -> list[SocialPost]:
    fetched_at = utc_now()
    posts: list[SocialPost] = []
    with path.expanduser().open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            lowered = {key.lower().strip(): value for key, value in row.items() if key}
            post_id = (
                lowered.get("video id")
                or lowered.get("post id")
                or lowered.get("id")
                or lowered.get("permalink")
                or f"tiktok_csv_row_{index}"
            )
            created_at = (
                lowered.get("date")
                or lowered.get("post date")
                or lowered.get("publish time")
                or lowered.get("created at")
            )
            text = lowered.get("caption") or lowered.get("description") or lowered.get("title")
            url = lowered.get("permalink") or lowered.get("url") or lowered.get("video url")

            metrics = {
                key: value
                for key, value in lowered.items()
                if key
                not in {
                    "video id",
                    "post id",
                    "id",
                    "permalink",
                    "url",
                    "video url",
                    "date",
                    "post date",
                    "publish time",
                    "created at",
                    "caption",
                    "description",
                    "title",
                }
            }
            posts.append(
                SocialPost(
                    platform="tiktok",
                    post_id=post_id,
                    post_url=url,
                    created_at=created_at,
                    text=text,
                    media_type="video",
                    metrics=metrics,
                    raw=row,
                    fetched_at=fetched_at,
                )
            )
    return posts


def write_posts(posts: list[SocialPost], out_path: Path, fmt: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        with out_path.open("w", encoding="utf-8") as handle:
            for post in posts:
                handle.write(json.dumps(asdict(post), ensure_ascii=False) + "\n")
        return

    fieldnames = [
        "platform",
        "post_id",
        "post_url",
        "created_at",
        "text",
        "media_type",
        "metrics",
        "raw",
        "fetched_at",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for post in posts:
            row = asdict(post)
            row["metrics"] = json.dumps(row["metrics"], ensure_ascii=False)
            row["raw"] = json.dumps(row["raw"], ensure_ascii=False)
            writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch social post analytics into JSONL/CSV.")
    parser.add_argument(
        "--platform",
        action="append",
        choices=["instagram", "threads", "bluesky", "x", "tiktok", "tiktok_csv", "all"],
        required=True,
        help="Repeat to fetch multiple platforms. 'all' excludes tiktok_csv.",
    )
    parser.add_argument("--limit", type=int, default=100, help="Max posts per platform.")
    parser.add_argument("--days", type=int, default=90, help="Only include posts from the last N days.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output path.")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    parser.add_argument("--bluesky-handle", default=os.getenv("BLUESKY_HANDLE"))
    parser.add_argument("--include-bluesky-reposts", action="store_true")
    parser.add_argument("--include-x-private-metrics", action="store_true")
    parser.add_argument("--tiktok-csv", type=Path, help="TikTok Business Suite analytics CSV export.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    platforms = set(args.platform)
    if "all" in platforms:
        platforms = {"instagram", "threads", "bluesky", "x", "tiktok"}

    all_posts: list[SocialPost] = []
    errors: dict[str, str] = {}

    for platform in sorted(platforms):
        try:
            if platform == "instagram":
                all_posts.extend(fetch_instagram(args.limit, args.days))
            elif platform == "threads":
                all_posts.extend(fetch_threads(args.limit, args.days))
            elif platform == "bluesky":
                if not args.bluesky_handle:
                    raise ApiError("Pass --bluesky-handle or set BLUESKY_HANDLE.")
                all_posts.extend(
                    fetch_bluesky(
                        args.bluesky_handle,
                        args.limit,
                        args.days,
                        args.include_bluesky_reposts,
                    )
                )
            elif platform == "x":
                all_posts.extend(fetch_x(args.limit, args.days, args.include_x_private_metrics))
            elif platform == "tiktok":
                all_posts.extend(fetch_tiktok_business(args.limit, args.days))
            elif platform == "tiktok_csv":
                if not args.tiktok_csv:
                    raise ApiError("Pass --tiktok-csv for TikTok CSV import.")
                all_posts.extend(import_tiktok_csv(args.tiktok_csv))
        except Exception as exc:  # Keep other platforms moving.
            errors[platform] = str(exc)

    write_posts(all_posts, Path(args.out), args.format)
    print(f"Wrote {len(all_posts)} posts to {args.out}", file=sys.stderr)
    if errors:
        print("Some platforms failed:", file=sys.stderr)
        for platform, error in errors.items():
            print(f"  - {platform}: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
