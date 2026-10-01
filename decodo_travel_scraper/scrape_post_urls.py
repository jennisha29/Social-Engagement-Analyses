from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


SUPPORTED_PLATFORMS = {"instagram", "threads"}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_url_file(path: Path, urls: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(urls) + "\n", encoding="utf-8")


def run_scrape(
    *,
    platform: str,
    url_file: Path,
    output_dir: Path,
    proxy_pool: str,
    xhr: bool,
    markdown: bool,
    browser_actions_json: Path | None,
) -> None:
    cmd = [
        sys.executable,
        str(Path(__file__).with_name("scrape_travel.py")),
        "--url-file",
        str(url_file),
        "--output-dir",
        str(output_dir),
        "--prefix",
        f"{platform}_posts",
        "--proxy-pool",
        proxy_pool,
        "--headless",
        "html",
    ]
    if xhr:
        cmd.append("--xhr")
    if markdown:
        cmd.append("--markdown")
    if browser_actions_json:
        cmd.extend(["--browser-actions-json", str(browser_actions_json)])
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Instagram/Threads individual post URLs via Decodo.")
    parser.add_argument("--post-urls-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/post_scrapes"))
    parser.add_argument("--platform", choices=["instagram", "threads", "all"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="Optional max URLs per platform.")
    parser.add_argument("--proxy-pool", choices=["standard", "premium"], default="premium")
    parser.add_argument("--xhr", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).with_name(".env"))
    parser.add_argument("--browser-actions-json", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)
    if not (os.getenv("DECODO_AUTH") or (os.getenv("DECODO_USERNAME") and os.getenv("DECODO_PASSWORD"))):
        raise SystemExit("Set DECODO_AUTH or DECODO_USERNAME/DECODO_PASSWORD before running.")

    rows = read_rows(args.post_urls_csv)
    platforms = SUPPORTED_PLATFORMS if args.platform == "all" else {args.platform}

    for platform in sorted(platforms):
        urls = [row["post_url"] for row in rows if row.get("platform") == platform]
        if args.limit:
            urls = urls[: args.limit]
        if not urls:
            print(f"No {platform} URLs found.")
            continue

        url_file = args.output_dir / f"{platform}_urls.txt"
        write_url_file(url_file, urls)
        print(f"Scraping {len(urls)} {platform} post URLs...")
        run_scrape(
            platform=platform,
            url_file=url_file,
            output_dir=args.output_dir,
            proxy_pool=args.proxy_pool,
            xhr=args.xhr,
            markdown=args.markdown,
            browser_actions_json=args.browser_actions_json,
        )


if __name__ == "__main__":
    main()
