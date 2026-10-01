from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError as error:
    raise SystemExit(
        "Missing dependency: beautifulsoup4. Install with:\n"
        "python3 -m pip install -r decodo_travel_scraper/requirements_browser.txt"
    ) from error

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options
except ImportError as error:
    raise SystemExit(
        "Missing dependency: selenium. Install with:\n"
        "python3 -m pip install -r decodo_travel_scraper/requirements_browser.txt"
    ) from error


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def slug(value: str) -> str:
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value[:90] or "page"


def read_urls(path: Path) -> list[str]:
    urls: list[str] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def browser_options(args: argparse.Namespace) -> Options:
    options = Options()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={args.window_width},{args.window_height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if args.user_agent:
        options.add_argument(f"--user-agent={args.user_agent}")
    if args.binary_location:
        options.binary_location = str(args.binary_location)
    if args.user_data_dir:
        options.add_argument(f"--user-data-dir={args.user_data_dir}")
    if args.profile_directory:
        options.add_argument(f"--profile-directory={args.profile_directory}")
    return options


def create_driver(args: argparse.Namespace):
    try:
        return webdriver.Chrome(options=browser_options(args))
    except WebDriverException as error:
        raise SystemExit(
            "Could not start Chrome/Chromium through Selenium.\n"
            "Check that Chrome or Chromium is installed, then retry.\n"
            f"Selenium error: {error}"
        ) from error


def scroll_page(driver, scrolls: int, pause_seconds: float) -> None:
    for _ in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_seconds)


def extract_page(url: str, html: str, html_path: Path, screenshot_path: Path | None) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = compact(soup.title.get_text(" ")) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    if not description_tag:
        description_tag = soup.find("meta", attrs={"property": "og:description"})
    meta_description = compact(description_tag.get("content", "")) if description_tag else ""

    text = compact(soup.get_text(" "))
    links = []
    for anchor in soup.find_all("a", href=True):
        label = compact(anchor.get_text(" "))
        href = anchor.get("href", "")
        if href:
            links.append({"text": label, "href": href})
        if len(links) >= 50:
            break

    images = []
    for image in soup.find_all("img"):
        src = image.get("src", "")
        alt = compact(image.get("alt", ""))
        if src or alt:
            images.append({"alt": alt, "src": src})
        if len(images) >= 25:
            break

    return {
        "url": url,
        "status": "ok",
        "title": title,
        "meta_description": meta_description,
        "text_preview": text[:3000],
        "link_count": len(soup.find_all("a", href=True)),
        "image_count": len(soup.find_all("img")),
        "links_json": json.dumps(links, ensure_ascii=False),
        "images_json": json.dumps(images, ensure_ascii=False),
        "html_path": str(html_path),
        "screenshot_path": str(screenshot_path or ""),
        "collected_at": utc_now(),
    }


def write_outputs(rows: list[dict[str, Any]], output_dir: Path, prefix: str, stamp: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{prefix}_{stamp}.csv"
    jsonl_path = output_dir / f"{prefix}_{stamp}.jsonl"
    fields = [
        "url",
        "status",
        "title",
        "meta_description",
        "text_preview",
        "link_count",
        "image_count",
        "links_json",
        "images_json",
        "html_path",
        "screenshot_path",
        "collected_at",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with jsonl_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {csv_path}")
    print(f"Wrote JSONL to {jsonl_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render permitted pages in Chrome/Chromium with Selenium, then parse with BeautifulSoup."
    )
    parser.add_argument("--url", action="append", default=[], help="URL to render. May be repeated.")
    parser.add_argument("--url-file", type=Path, help="Text file with one URL per line.")
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/selenium_chromium"))
    parser.add_argument("--prefix", default="selenium_pages")
    parser.add_argument("--wait-seconds", type=float, default=5)
    parser.add_argument("--scrolls", type=int, default=1)
    parser.add_argument("--scroll-pause-seconds", type=float, default=2)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--screenshot", action="store_true")
    parser.add_argument("--window-width", type=int, default=1440)
    parser.add_argument("--window-height", type=int, default=1200)
    parser.add_argument("--binary-location", type=Path, help="Optional Chrome/Chromium binary path.")
    parser.add_argument("--user-agent", help="Optional user agent string.")
    parser.add_argument("--user-data-dir", type=Path, help="Optional existing Chrome user data dir for owned/logged-in workflows.")
    parser.add_argument("--profile-directory", help="Optional Chrome profile directory name.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    urls = list(args.url)
    if args.url_file:
        urls.extend(read_urls(args.url_file))
    if not urls:
        raise SystemExit("Pass --url or --url-file.")

    stamp = utc_stamp()
    html_dir = args.output_dir / f"{args.prefix}_{stamp}_html"
    html_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = args.output_dir / f"{args.prefix}_{stamp}_screenshots"
    if args.screenshot:
        screenshot_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    driver = create_driver(args)
    try:
        for index, url in enumerate(urls, start=1):
            html_path = html_dir / f"{index:03d}_{slug(url)}.html"
            screenshot_path = screenshot_dir / f"{index:03d}_{slug(url)}.png" if args.screenshot else None
            try:
                driver.get(url)
                time.sleep(args.wait_seconds)
                scroll_page(driver, args.scrolls, args.scroll_pause_seconds)
                html = driver.page_source
                html_path.write_text(html, encoding="utf-8")
                if screenshot_path:
                    driver.save_screenshot(str(screenshot_path))
                rows.append(extract_page(url, html, html_path, screenshot_path))
                print(f"Rendered {index}/{len(urls)}: {url}")
            except Exception as error:
                rows.append(
                    {
                        "url": url,
                        "status": f"error: {error}",
                        "title": "",
                        "meta_description": "",
                        "text_preview": "",
                        "link_count": "",
                        "image_count": "",
                        "links_json": "[]",
                        "images_json": "[]",
                        "html_path": str(html_path),
                        "screenshot_path": str(screenshot_path or ""),
                        "collected_at": utc_now(),
                    }
                )
                print(f"Error rendering {url}: {error}", file=sys.stderr)
    finally:
        driver.quit()

    write_outputs(rows, args.output_dir, args.prefix, stamp)


if __name__ == "__main__":
    main()
