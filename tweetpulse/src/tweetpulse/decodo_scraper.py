from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DECODO_SCRAPE_URL = "https://scraper-api.decodo.com/v2/scrape"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def auth_header() -> str:
    token = os.getenv("DECODO_AUTH", "")
    if token:
        return f"Basic {token}"

    username = os.getenv("DECODO_USERNAME", "")
    password = os.getenv("DECODO_PASSWORD", "")
    if not username or not password:
        raise SystemExit(
            "Set DECODO_AUTH, or set DECODO_USERNAME and DECODO_PASSWORD."
        )
    encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": auth_header(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Decodo HTTP {error.code}: {detail}") from error


def scrape_url(
    url: str,
    *,
    endpoint: str = DECODO_SCRAPE_URL,
    proxy_pool: str = "premium",
    locale: str = "en-us",
    headless: str = "html",
    target: str = "universal",
) -> dict[str, Any]:
    payload = {
        "target": target,
        "url": url,
        "proxy_pool": proxy_pool,
        "headless": headless,
        "locale": locale,
    }
    return post_json(endpoint, payload)


def read_urls(path: Path) -> list[str]:
    urls: list[str] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def response_preview(payload: dict[str, Any], max_chars: int = 500) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    return text[:max_chars]


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(iter_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(iter_strings(item))
        return strings
    return []


def pick_page_text(payload: dict[str, Any]) -> str:
    priority_keys = {
        "content",
        "html",
        "body",
        "markdown",
        "text",
        "result",
        "results",
    }

    candidates: list[str] = []

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, child_key)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)
        elif isinstance(value, str):
            if key in priority_keys or len(value) > 200:
                candidates.append(value)

    walk(payload)
    if candidates:
        return max(candidates, key=len)
    strings = iter_strings(payload)
    return "\n".join(strings)


def strip_tags(text: str) -> str:
    import re

    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;?", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_match(pattern: str, text: str) -> str:
    import re

    match = re.search(pattern, text, flags=re.I | re.S)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def unique_matches(pattern: str, text: str, limit: int = 10) -> list[str]:
    import re

    seen: set[str] = set()
    values: list[str] = []
    for match in re.findall(pattern, text, flags=re.I):
        value = match if isinstance(match, str) else " ".join(match)
        value = " ".join(value.split())
        if value and value.lower() not in seen:
            seen.add(value.lower())
            values.append(value)
        if len(values) >= limit:
            break
    return values


def extract_travel_fields(payload: dict[str, Any]) -> dict[str, str]:
    page_text = pick_page_text(payload)
    visible_text = strip_tags(page_text)

    title = first_match(r"<title[^>]*>(.*?)</title>", page_text)
    meta_description = first_match(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        page_text,
    )
    if not meta_description:
        meta_description = first_match(
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
            page_text,
        )

    price_snippets = unique_matches(
        r"((?:USD\s*)?\$\s?\d{1,4}(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:per|/)\s*(?:night|day|person|traveler|room))?)",
        visible_text,
    )
    rating_snippets = unique_matches(
        r"((?:rated\s*)?\d(?:\.\d)?\s*(?:/|out of)\s*5|(?:rated\s*)?\d(?:\.\d)?\s*(?:/|out of)\s*10|\d(?:\.\d)?\s*stars?)",
        visible_text,
    )
    date_snippets = unique_matches(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?)",
        visible_text,
    )

    travel_terms = [
        "hotel",
        "flight",
        "airline",
        "airport",
        "room",
        "night",
        "guest",
        "check-in",
        "check out",
        "booking",
        "resort",
        "vacation",
        "rental car",
    ]
    lowered = visible_text.lower()
    matched_terms = [term for term in travel_terms if term in lowered]

    return {
        "title": title,
        "meta_description": meta_description,
        "price_snippets": " | ".join(price_snippets),
        "rating_snippets": " | ".join(rating_snippets),
        "date_snippets": " | ".join(date_snippets),
        "travel_terms": " | ".join(matched_terms),
        "visible_text_preview": visible_text[:1000],
    }


def write_outputs(rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    jsonl_path = output_dir / f"{prefix}_{stamp}.jsonl"
    csv_path = output_dir / f"{prefix}_{stamp}.csv"

    with jsonl_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        fields = [
            "url",
            "status",
            "title",
            "meta_description",
            "price_snippets",
            "rating_snippets",
            "date_snippets",
            "travel_terms",
            "visible_text_preview",
            "preview",
            "raw",
            "collected_at",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {csv_path}")
    print(f"Wrote raw JSONL to {jsonl_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape public/allowed pages with Decodo Web Scraping API."
    )
    parser.add_argument("--url", action="append", default=[], help="URL to scrape. May be repeated.")
    parser.add_argument("--url-file", type=Path, help="Text file with one URL per line.")
    parser.add_argument("--output-dir", type=Path, default=Path("tweetpulse/data/decodo"))
    parser.add_argument("--prefix", default="decodo_scrape")
    parser.add_argument("--proxy-pool", default="premium", choices=["standard", "premium"])
    parser.add_argument("--locale", default="en-us")
    parser.add_argument("--headless", default="html")
    parser.add_argument("--target", default="universal")
    parser.add_argument("--endpoint", default=DECODO_SCRAPE_URL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    urls = list(args.url)
    if args.url_file:
        urls.extend(read_urls(args.url_file))
    if not urls:
        raise SystemExit("Pass --url or --url-file.")

    rows: list[dict[str, Any]] = []
    for url in urls:
        try:
            payload = scrape_url(
                url,
                endpoint=args.endpoint,
                proxy_pool=args.proxy_pool,
                locale=args.locale,
                headless=args.headless,
                target=args.target,
            )
            extracted = extract_travel_fields(payload)
            rows.append(
                {
                    "url": url,
                    "status": "ok",
                    **extracted,
                    "preview": response_preview(payload),
                    "raw": json.dumps(payload, ensure_ascii=False),
                    "collected_at": utc_now(),
                }
            )
        except Exception as error:
            rows.append(
                {
                    "url": url,
                    "status": f"error: {error}",
                    "title": "",
                    "meta_description": "",
                    "price_snippets": "",
                    "rating_snippets": "",
                    "date_snippets": "",
                    "travel_terms": "",
                    "visible_text_preview": "",
                    "preview": "",
                    "raw": "",
                    "collected_at": utc_now(),
                }
            )

    write_outputs(rows, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
