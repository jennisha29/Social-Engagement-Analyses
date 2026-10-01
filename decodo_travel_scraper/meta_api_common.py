from __future__ import annotations

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
    "views",
    "reach",
    "saved",
    "total_interactions",
    "image_url",
    "media_type",
    "scraped_at",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_json(url: str, params: dict[str, str], timeout: int = 90) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request_url = f"{url}?{query}" if query else url
    request = urllib.request.Request(request_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} for {url}: {detail}") from error


def paginate(
    url: str,
    params: dict[str, str],
    *,
    limit: int,
    sleep_seconds: float = 0.2,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    next_url: str | None = url
    next_params: dict[str, str] = dict(params)

    while next_url:
        payload = get_json(next_url, next_params)
        page_rows = payload.get("data", [])
        if isinstance(page_rows, list):
            rows.extend(page_rows)
        if limit and len(rows) >= limit:
            return rows[:limit]
        paging = payload.get("paging", {}) if isinstance(payload, dict) else {}
        cursors_next = paging.get("next") if isinstance(paging, dict) else None
        if not cursors_next:
            break
        next_url = cursors_next
        next_params = {}
        time.sleep(sleep_seconds)
    return rows


def write_outputs(rows: list[dict[str, str]], raw_rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    csv_path = output_dir / f"{prefix}_{stamp}.csv"
    jsonl_path = output_dir / f"{prefix}_{stamp}.jsonl"
    raw_path = output_dir / f"{prefix}_{stamp}_raw.jsonl"

    fields = list(MASTER_FIELDS)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    with jsonl_path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    with raw_path.open("w", encoding="utf-8") as file:
        for row in raw_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to {csv_path}")
    print(f"Wrote normalized JSONL to {jsonl_path}")
    print(f"Wrote raw API JSONL to {raw_path}")
