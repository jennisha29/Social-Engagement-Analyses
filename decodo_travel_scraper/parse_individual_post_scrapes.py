from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path


MASTER_FIELDS = [
    "platform",
    "author_handle",
    "post_url",
    "post_id",
    "threads_internal_id",
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


def raw_payload(row: dict) -> dict:
    try:
        return json.loads(row.get("raw", ""))
    except Exception:
        return {}


def raw_html(row: dict) -> str:
    payload = raw_payload(row)
    return max(iter_strings(payload), key=len, default="")


def markdown_content(row: dict) -> str:
    payload = raw_payload(row)
    if isinstance(payload, dict):
        for result in payload.get("results", []):
            if isinstance(result, dict) and result.get("type") == "markdown":
                content = result.get("content", "")
                if isinstance(content, str):
                    return content
    return ""


def response_bodies(row: dict) -> list[str]:
    payload = raw_payload(row)
    bodies: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "response_body" and isinstance(child, str):
                    bodies.append(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return bodies


def parse_prefixed_json(value: str):
    value = value.strip()
    if value.startswith("for (;;);"):
        value = value[len("for (;;);") :]
    try:
        return json.loads(value)
    except Exception:
        return None


def find_route_meta_title(row: dict, post_id_value: str) -> str:
    for body in response_bodies(row):
        if post_id_value not in body:
            continue
        data = parse_prefixed_json(body)
        if not data:
            continue
        titles: list[str] = []

        def walk(value):
            if isinstance(value, dict):
                meta = value.get("meta")
                if isinstance(meta, dict) and isinstance(meta.get("title"), str):
                    titles.append(meta["title"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(data)
        for title in titles:
            if title and "Goods Unite Us" not in title:
                return compact(title)
        if titles:
            return compact(titles[0])
    return ""


def find_threads_internal_id(row: dict, post_id_value: str) -> str:
    for body in response_bodies(row):
        if post_id_value not in body:
            continue
        data = parse_prefixed_json(body)
        if not data:
            continue
        ids: list[str] = []

        def walk(value):
            if isinstance(value, dict):
                props = value.get("props")
                if isinstance(props, dict) and isinstance(props.get("post_id"), str):
                    ids.append(props["post_id"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(data)
        if ids:
            return ids[0]
    return ""


def visible_text(row: dict) -> str:
    return strip_tags(raw_html(row) or row.get("visible_text_preview", ""))


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


def post_id(platform: str, url: str) -> str:
    value = url.rstrip("/").rsplit("/", 1)[-1]
    return value


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I | re.S)
    return compact(match.group(1)) if match else ""


def parse_count(value: str) -> str:
    value = compact(value).replace(",", "")
    match = re.match(r"([\d.]+)\s*([KkMm]?)", value)
    if not match:
        return ""
    number = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        number *= 1000
    elif suffix == "m":
        number *= 1_000_000
    return str(int(number))


def markdown_links_to_text(text: str) -> str:
    text = re.sub(r"!\[(.*?)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", text)
    return compact(text)


def instagram_markdown_caption(markdown: str) -> str:
    match = re.search(
        r"\[goodsuniteus\]\(/goodsuniteus/\)(?:[ \t]|\xa0)+[^\n]+\n\n(.*?)(?:\n\nLoad more comments|\n\nView all|\n\nLike\n\n)",
        markdown,
        flags=re.I | re.S,
    )
    if not match:
        return ""
    return markdown_links_to_text(match.group(1))


def instagram_markdown_author(markdown: str) -> str:
    match = re.search(
        r"\[([^\]]+)\]\(/([^/]+)/\)(?:[ \t]|\xa0)+[^\n]+\n\n",
        markdown,
        flags=re.I,
    )
    if not match:
        return ""
    return compact(match.group(2)).lower()


def instagram_markdown_image(markdown: str) -> str:
    for alt, image_url in re.findall(r"!\[(.*?)\]\((https://[^)]+)\)", markdown, flags=re.S):
        if "profile picture" in alt.lower():
            continue
        return image_url
    return ""


def instagram_markdown_date(markdown: str) -> str:
    match = re.search(
        r"!\[(?:Photo|Video) by .*? on ([A-Za-z]+ \d{1,2}, \d{4})",
        markdown,
        flags=re.S,
    )
    if not match:
        return ""
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").date().isoformat()
    except ValueError:
        return ""


def instagram_markdown_likes(markdown: str) -> str:
    return parse_count(first_match(r"\nLike\n\n([\d,.]+[KkMm]?)\n\nComment", markdown))


def instagram_markdown_comments(markdown: str) -> str:
    if re.search(r"\bNo comments yet\.", markdown, flags=re.I):
        return "0"
    count = first_match(r"View all\s+([\d,.]+[KkMm]?)\s+comments", markdown)
    return parse_count(count)


def image_url_from_html(html: str) -> str:
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']',
        r'"image"\s*:\s*"([^"]+)"',
    ]:
        found = first_match(pattern, html)
        if found:
            return found
    return ""


def media_type_from_url_and_html(url: str, html: str) -> str:
    if "/reel/" in url or "video" in html[:5000].lower():
        return "video"
    if image_url_from_html(html):
        return "image"
    return "text"


def parse_instagram(row: dict) -> dict[str, str]:
    url = row["url"]
    html = raw_html(row)
    markdown = markdown_content(row)
    text = visible_text(row)
    title = row.get("title", "")
    caption = instagram_markdown_caption(markdown)
    if not caption:
        caption = first_match(r"^[^-]+-\s+(.*?)\s+on Instagram", title)
    if not caption:
        caption = first_match(r'property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html)
    likes = instagram_markdown_likes(markdown)
    if not likes:
        likes = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+likes", text))
    comments = instagram_markdown_comments(markdown)
    if not comments:
        comments = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+comments", text))
    published_at = instagram_markdown_date(markdown)
    if not published_at:
        published_at = first_match(r'"datePublished"\s*:\s*"([^"]+)"', html)
    image_url = instagram_markdown_image(markdown) or image_url_from_html(html)
    media_type = media_type_from_url_and_html(url, html)
    if image_url and media_type == "text":
        media_type = "image"

    return {
        "platform": "instagram",
        "author_handle": instagram_markdown_author(markdown) or "goodsuniteus",
        "post_url": url,
        "post_id": post_id("instagram", url),
        "threads_internal_id": "",
        "published_at": published_at,
        "post_text": caption,
        "likes": likes,
        "comments": comments,
        "replies": "",
        "shares": "",
        "reposts": "",
        "quotes": "",
        "image_url": image_url,
        "media_type": media_type,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def parse_threads(row: dict) -> dict[str, str]:
    url = row["url"]
    shortcode = post_id("threads", url)
    html = raw_html(row)
    text = visible_text(row)
    title = row.get("title", "")
    post_text = first_match(r"Goods Unite Us on Threads:\s*[\"“](.*?)[\"”]", title)
    if not post_text:
        post_text = find_route_meta_title(row, shortcode)
    if not post_text:
        post_text = first_match(r"goodsuniteus\s+.*?More\s+(.*?)\s+Like", text)
    published_at = first_match(r'"datePublished"\s*:\s*"([^"]+)"', html)
    likes = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+likes?", text))
    replies = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+repl(?:y|ies)", text))
    reposts = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+reposts?", text))
    quotes = parse_count(first_match(r"([\d,.]+[KkMm]?)\s+quotes?", text))

    return {
        "platform": "threads",
        "author_handle": "goodsuniteus",
        "post_url": url,
        "post_id": shortcode,
        "threads_internal_id": find_threads_internal_id(row, shortcode),
        "published_at": published_at,
        "post_text": post_text,
        "likes": likes,
        "comments": "",
        "replies": replies,
        "shares": "",
        "reposts": reposts,
        "quotes": quotes,
        "image_url": image_url_from_html(html),
        "media_type": media_type_from_url_and_html(url, html),
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def parse_jsonl(path: Path) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        platform = platform_for_url(row.get("url", ""))
        if platform == "instagram":
            parsed.append(parse_instagram(row))
        elif platform == "threads":
            parsed.append(parse_threads(row))
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse individual Instagram/Threads post Decodo scrapes.")
    parser.add_argument("jsonl", type=Path, nargs="+")
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for path in args.jsonl:
        for row in parse_jsonl(path):
            key = (row["platform"], row["post_url"])
            if key not in seen:
                seen.add(key)
                rows.append(row)

    with args.output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MASTER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} parsed post rows to {args.output_csv}")


if __name__ == "__main__":
    main()
