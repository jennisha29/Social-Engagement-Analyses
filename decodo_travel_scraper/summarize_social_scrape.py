from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def match(pattern: str, text: str) -> str:
    result = re.search(pattern, text, flags=re.I)
    return compact(result.group(1)) if result else ""


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


def summarize_row(row: dict[str, str]) -> dict[str, str]:
    url = row.get("url", "")
    platform = platform_for_url(url)
    text = compact(row.get("visible_text_preview", ""))
    title = compact(row.get("title", ""))
    description = compact(row.get("meta_description", ""))

    followers = ""
    following = ""
    posts = ""
    bio = description

    if platform == "instagram":
        followers = match(r"Options\s+([^ ]+\s+followers)", text)
        following = match(r"followers\s+([^ ]+\s+following)", text)
        bio = match(r"Goods Unite Us Threads goodsuniteus\s+(.*?)\s+Link icon", text) or description
    elif platform == "threads":
        followers = match(r"(\d[\d,.Kk]*\s+followers)", text)
        posts = match(r"(\d[\d,.Kk]*\s+Threads)", description)
        bio = match(r"goodsuniteus Goods Unite Us goodsuniteus\s+(.*?)\s+apps\.apple\.com", text) or description
    elif platform == "x":
        posts = match(r"Goods Unite Us\s+([\d,]+\s+posts)", text)
        following = match(r"Joined May 2017\s+([\d,]+\s+Following)", text)
        followers = match(r"Following\s+([\d,]+\s+Followers)", text)
        bio = description
    elif platform == "bluesky":
        followers = match(r"(\d[\d,.]*\s+Follower)", text)
        following = match(r"Follower\s+(\d[\d,.]*\s+Folge ich)", text)
        posts = match(r"Folge ich\s+(\d[\d,.]*\s+Posts)", text)
        bio = description

    return {
        "platform": platform,
        "url": url,
        "status": row.get("status", ""),
        "title": title,
        "followers": followers,
        "following": following,
        "posts_or_threads": posts,
        "bio_or_description": compact(bio),
        "visible_text_preview": text[:1200],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Decodo social profile scrape output.")
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [json.loads(line) for line in args.jsonl.open(encoding="utf-8")]
    summaries = [summarize_row(row) for row in rows]

    output_csv = args.output_csv or args.jsonl.with_name(args.jsonl.stem + "_social_summary.csv")
    output_md = args.output_md or args.jsonl.with_name(args.jsonl.stem + "_social_summary.md")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(summaries[0].keys()))
        writer.writeheader()
        writer.writerows(summaries)

    lines = ["# Social Profile Scrape Summary", ""]
    for item in summaries:
        lines.append(f"## {item['platform'].title()}")
        lines.append("")
        lines.append(f"- URL: {item['url']}")
        lines.append(f"- Status: {item['status']}")
        lines.append(f"- Title: {item['title']}")
        if item["followers"]:
            lines.append(f"- Followers: {item['followers']}")
        if item["following"]:
            lines.append(f"- Following: {item['following']}")
        if item["posts_or_threads"]:
            lines.append(f"- Posts/Threads: {item['posts_or_threads']}")
        lines.append(f"- Bio/Description: {item['bio_or_description']}")
        lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")


if __name__ == "__main__":
    main()
