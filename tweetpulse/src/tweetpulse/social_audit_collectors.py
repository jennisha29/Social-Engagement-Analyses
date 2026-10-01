from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


BLUESKY_API = "https://public.api.bsky.app/xrpc"
X_API = "https://api.x.com/2"
GRAPH_API = "https://graph.facebook.com/v21.0"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code == 429 and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {error.code} for {url}: {detail}") from error
        except urllib.error.URLError as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Could not fetch {url}: {error}") from error
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "platform",
        "post_id",
        "post_url",
        "published_at",
        "author",
        "text",
        "media_type",
        "views",
        "impressions",
        "reach",
        "likes",
        "comments",
        "replies",
        "shares",
        "reposts",
        "quotes",
        "saves",
        "bookmarks",
        "link_clicks",
        "raw",
        "collected_at",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def detect_bluesky_media(post: dict[str, Any]) -> str:
    embed_type = post.get("record", {}).get("embed", {}).get("$type", "")
    if "video" in embed_type:
        return "video"
    if "images" in embed_type:
        return "image"
    if "external" in embed_type:
        return "external_link"
    return "text"


def bluesky_post_url(handle: str, uri: str) -> str:
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def fetch_bluesky_author_feed(
    actor: str,
    *,
    max_posts: int = 100,
    include_reposts: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = ""
    filter_value = "posts_with_replies" if include_reposts else "posts_no_replies"

    while len(rows) < max_posts:
        params = {
            "actor": actor,
            "limit": min(100, max_posts - len(rows)),
            "filter": filter_value,
        }
        if cursor:
            params["cursor"] = cursor
        url = f"{BLUESKY_API}/app.bsky.feed.getAuthorFeed?{urllib.parse.urlencode(params)}"
        payload = get_json(url)
        for item in payload.get("feed", []):
            if not include_reposts and item.get("reason"):
                continue
            post = item.get("post", {})
            record = post.get("record", {})
            rows.append(
                {
                    "platform": "bluesky",
                    "post_id": post.get("uri", ""),
                    "post_url": bluesky_post_url(actor, post.get("uri", "")),
                    "published_at": record.get("createdAt", ""),
                    "author": actor,
                    "text": record.get("text", ""),
                    "media_type": detect_bluesky_media(post),
                    "views": "",
                    "impressions": "",
                    "reach": "",
                    "likes": post.get("likeCount", 0),
                    "comments": "",
                    "replies": post.get("replyCount", 0),
                    "shares": "",
                    "reposts": post.get("repostCount", 0),
                    "quotes": post.get("quoteCount", 0),
                    "saves": "",
                    "bookmarks": post.get("bookmarkCount", 0),
                    "link_clicks": "",
                    "raw": json.dumps(post, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
            if len(rows) >= max_posts:
                break
        cursor = payload.get("cursor", "")
        if not cursor or not payload.get("feed"):
            break
    return rows


def search_bluesky_posts(query: str, *, max_posts: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = ""
    while len(rows) < max_posts:
        params = {"q": query, "limit": min(100, max_posts - len(rows))}
        if cursor:
            params["cursor"] = cursor
        url = f"{BLUESKY_API}/app.bsky.feed.searchPosts?{urllib.parse.urlencode(params)}"
        payload = get_json(url)
        for post in payload.get("posts", []):
            record = post.get("record", {})
            author = post.get("author", {}).get("handle", "")
            rows.append(
                {
                    "platform": "bluesky",
                    "post_id": post.get("uri", ""),
                    "post_url": bluesky_post_url(author, post.get("uri", "")),
                    "published_at": record.get("createdAt", ""),
                    "author": author,
                    "text": record.get("text", ""),
                    "media_type": detect_bluesky_media(post),
                    "views": "",
                    "impressions": "",
                    "reach": "",
                    "likes": post.get("likeCount", 0),
                    "comments": "",
                    "replies": post.get("replyCount", 0),
                    "shares": "",
                    "reposts": post.get("repostCount", 0),
                    "quotes": post.get("quoteCount", 0),
                    "saves": "",
                    "bookmarks": post.get("bookmarkCount", 0),
                    "link_clicks": "",
                    "raw": json.dumps(post, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
        cursor = payload.get("cursor", "")
        if not cursor or not payload.get("posts"):
            break
    return rows


def fetch_x_user_posts(
    username: str,
    *,
    bearer_token: str,
    max_posts: int = 100,
) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    user_url = f"{X_API}/users/by/username/{urllib.parse.quote(username)}"
    user = get_json(user_url, headers=headers).get("data", {})
    user_id = user.get("id")
    if not user_id:
        raise RuntimeError(f"Could not resolve X username: {username}")

    rows: list[dict[str, Any]] = []
    pagination_token = ""
    fields = ",".join(
        [
            "created_at",
            "public_metrics",
            "organic_metrics",
            "non_public_metrics",
            "text",
        ]
    )
    while len(rows) < max_posts:
        params = {
            "max_results": min(100, max_posts - len(rows)),
            "tweet.fields": fields,
            "exclude": "retweets,replies",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        url = f"{X_API}/users/{user_id}/tweets?{urllib.parse.urlencode(params)}"
        payload = get_json(url, headers=headers)
        for post in payload.get("data", []):
            public_metrics = post.get("public_metrics", {})
            organic_metrics = post.get("organic_metrics", {})
            non_public_metrics = post.get("non_public_metrics", {})
            rows.append(
                {
                    "platform": "x",
                    "post_id": post.get("id", ""),
                    "post_url": f"https://x.com/{username}/status/{post.get('id', '')}",
                    "published_at": post.get("created_at", ""),
                    "author": username,
                    "text": post.get("text", ""),
                    "media_type": "",
                    "views": organic_metrics.get("impression_count", ""),
                    "impressions": organic_metrics.get("impression_count", ""),
                    "reach": "",
                    "likes": public_metrics.get("like_count", 0),
                    "comments": "",
                    "replies": public_metrics.get("reply_count", 0),
                    "shares": "",
                    "reposts": public_metrics.get("retweet_count", 0),
                    "quotes": public_metrics.get("quote_count", 0),
                    "saves": "",
                    "bookmarks": public_metrics.get(
                        "bookmark_count", non_public_metrics.get("bookmark_count", "")
                    ),
                    "link_clicks": organic_metrics.get("url_link_clicks", ""),
                    "raw": json.dumps(post, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
        pagination_token = payload.get("meta", {}).get("next_token", "")
        if not pagination_token or not payload.get("data"):
            break
    return rows


def fetch_instagram_media_insights(
    ig_user_id: str,
    *,
    access_token: str,
    max_posts: int = 100,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = "id,caption,media_type,permalink,timestamp,like_count,comments_count"
    media_url = (
        f"{GRAPH_API}/{ig_user_id}/media?"
        f"{urllib.parse.urlencode({'fields': fields, 'limit': min(100, max_posts), 'access_token': access_token})}"
    )

    while media_url and len(rows) < max_posts:
        payload = get_json(media_url)
        for media in payload.get("data", []):
            media_id = media.get("id", "")
            metric_names = "views,reach,likes,comments,saved,shares,total_interactions"
            insights_url = (
                f"{GRAPH_API}/{media_id}/insights?"
                f"{urllib.parse.urlencode({'metric': metric_names, 'access_token': access_token})}"
            )
            insights = {}
            try:
                insight_payload = get_json(insights_url)
                for item in insight_payload.get("data", []):
                    values = item.get("values", [])
                    insights[item.get("name", "")] = values[-1].get("value", "") if values else ""
            except RuntimeError as error:
                insights["error"] = str(error)

            rows.append(
                {
                    "platform": "instagram",
                    "post_id": media_id,
                    "post_url": media.get("permalink", ""),
                    "published_at": media.get("timestamp", ""),
                    "author": ig_user_id,
                    "text": media.get("caption", ""),
                    "media_type": media.get("media_type", ""),
                    "views": insights.get("views", ""),
                    "impressions": "",
                    "reach": insights.get("reach", ""),
                    "likes": insights.get("likes", media.get("like_count", "")),
                    "comments": insights.get("comments", media.get("comments_count", "")),
                    "replies": "",
                    "shares": insights.get("shares", ""),
                    "reposts": "",
                    "quotes": "",
                    "saves": insights.get("saved", ""),
                    "bookmarks": "",
                    "link_clicks": "",
                    "raw": json.dumps({"media": media, "insights": insights}, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
            if len(rows) >= max_posts:
                break
        media_url = payload.get("paging", {}).get("next", "")
    return rows


def fetch_threads_media_insights(
    *,
    access_token: str,
    max_posts: int = 100,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = "id,permalink,text,timestamp,media_type"
    threads_url = (
        f"{GRAPH_API}/me/threads?"
        f"{urllib.parse.urlencode({'fields': fields, 'limit': min(100, max_posts), 'access_token': access_token})}"
    )

    while threads_url and len(rows) < max_posts:
        payload = get_json(threads_url)
        for thread in payload.get("data", []):
            thread_id = thread.get("id", "")
            metric_names = "views,likes,replies,reposts,quotes,shares"
            insights_url = (
                f"{GRAPH_API}/{thread_id}/insights?"
                f"{urllib.parse.urlencode({'metric': metric_names, 'access_token': access_token})}"
            )
            insights = {}
            try:
                insight_payload = get_json(insights_url)
                for item in insight_payload.get("data", []):
                    values = item.get("values", [])
                    insights[item.get("name", "")] = values[-1].get("value", "") if values else ""
            except RuntimeError as error:
                insights["error"] = str(error)

            rows.append(
                {
                    "platform": "threads",
                    "post_id": thread_id,
                    "post_url": thread.get("permalink", ""),
                    "published_at": thread.get("timestamp", ""),
                    "author": "me",
                    "text": thread.get("text", ""),
                    "media_type": thread.get("media_type", ""),
                    "views": insights.get("views", ""),
                    "impressions": "",
                    "reach": "",
                    "likes": insights.get("likes", ""),
                    "comments": "",
                    "replies": insights.get("replies", ""),
                    "shares": insights.get("shares", ""),
                    "reposts": insights.get("reposts", ""),
                    "quotes": insights.get("quotes", ""),
                    "saves": "",
                    "bookmarks": "",
                    "link_clicks": "",
                    "raw": json.dumps({"thread": thread, "insights": insights}, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
            if len(rows) >= max_posts:
                break
        threads_url = payload.get("paging", {}).get("next", "")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Goods Unite Us social posts through official APIs and native-friendly endpoints."
    )
    parser.add_argument("--platform", choices=["bluesky", "x", "instagram", "threads"], required=True)
    parser.add_argument("--max-posts", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=Path("tweetpulse/data/social_audit"))
    parser.add_argument("--bluesky-actor", default="goodsuniteus.bsky.social")
    parser.add_argument("--bluesky-query", default="")
    parser.add_argument("--x-username", default="goodsuniteus")
    parser.add_argument("--x-bearer-token", default=os.getenv("X_BEARER_TOKEN", ""))
    parser.add_argument("--instagram-user-id", default=os.getenv("INSTAGRAM_USER_ID", ""))
    parser.add_argument("--instagram-access-token", default=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""))
    parser.add_argument("--threads-access-token", default=os.getenv("THREADS_ACCESS_TOKEN", ""))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.platform == "bluesky":
        if args.bluesky_query:
            rows = search_bluesky_posts(args.bluesky_query, max_posts=args.max_posts)
        else:
            rows = fetch_bluesky_author_feed(args.bluesky_actor, max_posts=args.max_posts)
    elif args.platform == "x":
        if not args.x_bearer_token:
            raise SystemExit("Set X_BEARER_TOKEN or pass --x-bearer-token.")
        rows = fetch_x_user_posts(
            args.x_username,
            bearer_token=args.x_bearer_token,
            max_posts=args.max_posts,
        )
    elif args.platform == "instagram":
        if not args.instagram_user_id or not args.instagram_access_token:
            raise SystemExit("Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN.")
        rows = fetch_instagram_media_insights(
            args.instagram_user_id,
            access_token=args.instagram_access_token,
            max_posts=args.max_posts,
        )
    elif args.platform == "threads":
        if not args.threads_access_token:
            raise SystemExit("Set THREADS_ACCESS_TOKEN.")
        rows = fetch_threads_media_insights(
            access_token=args.threads_access_token,
            max_posts=args.max_posts,
        )
    else:
        raise SystemExit(f"Unsupported platform: {args.platform}")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = args.output_dir / f"{args.platform}_{timestamp}"
    write_jsonl(rows, base.with_suffix(".jsonl"))
    write_csv(rows, base.with_suffix(".csv"))
    print(f"Wrote {len(rows)} rows to {base.with_suffix('.csv')}")
    print(f"Wrote raw JSONL to {base.with_suffix('.jsonl')}")


if __name__ == "__main__":
    main()
