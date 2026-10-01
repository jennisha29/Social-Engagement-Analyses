from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def strip_tags(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"&#x27;", "'", text)
    text = re.sub(r"&quot;", '"', text)
    return compact(text)


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def raw_text(row: dict) -> str:
    raw = row.get("raw", "")
    try:
        payload = json.loads(raw)
    except Exception:
        return compact(row.get("visible_text_preview", ""))
    longest = max(iter_strings(payload), key=len, default="")
    return strip_tags(longest)


def platform_for_url(url: str) -> str:
    if "instagram.com" in url:
        return "instagram"
    if "threads.com" in url:
        return "threads"
    if "x.com" in url:
        return "x"
    if "bsky.app" in url:
        return "bluesky"
    return "unknown"


def clean_post(text: str) -> str:
    text = compact(text)
    text = re.sub(r"\s+(Like|Comment|Repost|Share)(\s+|$).*", "", text, flags=re.I)
    text = re.sub(r"\s+(Show more|More)$", "", text, flags=re.I)
    return text.strip(" -·")


def extract_threads(text: str) -> list[str]:
    pattern = r"goodsuniteus\s+\d+[hd]\s+More\s+(.*?)(?=\s+Like\s+|goodsuniteus\s+\d+[hd]\s+More\s+|$)"
    return [clean_post(value) for value in re.findall(pattern, text, flags=re.I) if clean_post(value)]


def extract_x(text: str) -> list[str]:
    pattern = r"Goods Unite Us @goodsuniteus\s+(\w{3}\s+\d+|\d+[hm])\s+(.*?)(?=\s+Goods Unite Us @goodsuniteus\s+|\s+\d+\s+\d+\s+\d+|$)"
    posts = []
    for date_or_age, value in re.findall(pattern, text, flags=re.I):
        post = clean_post(f"{date_or_age}: {value}")
        if post:
            posts.append(post)
    return posts


def extract_bluesky(text: str) -> list[str]:
    pattern = r"GoodsUniteUs @goodsuniteus\.bsky\.social\s+·\s+([^\.]+?\.)\s+(.*?)(?=\s+GoodsUniteUs @goodsuniteus\.bsky\.social\s+·|$)"
    posts = []
    for age, value in re.findall(pattern, text, flags=re.I):
        post = clean_post(f"{age} {value}")
        if post:
            posts.append(post)
    return posts


def extract_instagram(text: str) -> list[str]:
    if "Show more posts from goodsuniteus" in text:
        return ["Instagram profile loaded, but recent post captions were not exposed in scrape text."]
    return []


def extract_posts(row: dict) -> list[dict[str, str]]:
    url = row.get("url", "")
    platform = platform_for_url(url)
    text = raw_text(row)
    if platform == "threads":
        posts = extract_threads(text)
    elif platform == "x":
        posts = extract_x(text)
    elif platform == "bluesky":
        posts = extract_bluesky(text)
    elif platform == "instagram":
        posts = extract_instagram(text)
    else:
        posts = []

    deduped = []
    seen = set()
    for post in posts:
        key = post.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(post)

    return [
        {
            "platform": platform,
            "source_url": url,
            "post_text": post,
            "text_length": str(len(post)),
        }
        for post in deduped
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract visible social post snippets from Decodo JSONL.")
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [json.loads(line) for line in args.jsonl.open(encoding="utf-8")]
    posts = []
    for row in rows:
        posts.extend(extract_posts(row))

    output_csv = args.output_csv or args.jsonl.with_name(args.jsonl.stem + "_visible_posts.csv")
    output_md = args.output_md or args.jsonl.with_name(args.jsonl.stem + "_visible_posts.md")

    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["platform", "source_url", "post_text", "text_length"])
        writer.writeheader()
        writer.writerows(posts)

    lines = ["# Visible Social Post Snippets", ""]
    for idx, post in enumerate(posts, 1):
        lines.append(f"{idx}. **{post['platform']}**: {post['post_text']}")
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {len(posts)} posts to {output_csv}")
    print(f"Wrote markdown summary to {output_md}")


if __name__ == "__main__":
    main()
