from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from scrape_travel import extract_travel_fields, scrape_url, utc_now, write_outputs


DEFAULT_ACTIONS = Path(__file__).with_name("instagram_rendered_actions.json")
DEFAULT_URLS = Path(__file__).parent / "outputs" / "post_scrapes" / "instagram_urls.txt"
DEFAULT_OUTPUT = Path(__file__).parent / "outputs" / "instagram_rendered_tests"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def first_url(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    raise SystemExit(f"No Instagram URLs found in {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test one Instagram post with Decodo JS rendering and browser actions."
    )
    parser.add_argument("--url", help="Instagram post URL. Defaults to the first instagram_urls.txt entry.")
    parser.add_argument("--url-file", type=Path, default=DEFAULT_URLS)
    parser.add_argument("--actions-json", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--env-file", type=Path, default=Path(__file__).with_name(".env"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prefix", default="instagram_rendered_post")
    parser.add_argument("--proxy-pool", default="premium", choices=["standard", "premium"])
    parser.add_argument("--locale", default="en-us")
    parser.add_argument("--headless", default="html")
    parser.add_argument("--target", default="universal")
    parser.add_argument("--xhr", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)

    url = args.url or first_url(args.url_file)
    browser_actions = json.loads(args.actions_json.read_text(encoding="utf-8"))
    payload = scrape_url(
        url,
        endpoint="https://scraper-api.decodo.com/v2/scrape",
        proxy_pool=args.proxy_pool,
        locale=args.locale,
        headless=args.headless,
        target=args.target,
        xhr=args.xhr,
        markdown=args.markdown,
        parse=False,
        browser_actions=browser_actions,
    )
    rows = [
        {
            "url": url,
            "status": "ok",
            **extract_travel_fields(payload),
            "raw": json.dumps(payload, ensure_ascii=False),
            "collected_at": utc_now(),
        }
    ]
    write_outputs(rows, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
