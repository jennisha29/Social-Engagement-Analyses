from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


FIELDS = [
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
    "total_engagements",
    "platform_percentile",
    "data_quality",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def has_value(value: str) -> bool:
    return str(value or "").strip() != ""


def to_int(value: str) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def engagement_keys(platform: str) -> list[str]:
    if platform == "instagram":
        return ["likes", "comments", "shares"]
    if platform == "bluesky":
        return ["likes", "replies", "reposts", "quotes"]
    if platform == "threads":
        return ["likes", "replies", "reposts", "quotes", "shares"]
    if platform == "x":
        return ["likes", "replies", "reposts", "quotes"]
    return ["likes", "comments", "replies", "shares", "reposts", "quotes"]


def engagement(row: dict[str, str]) -> str:
    if row.get("platform") == "instagram" and row.get("author_handle") not in {"", "goodsuniteus"}:
        return ""
    keys = engagement_keys(row.get("platform", ""))
    available_values = [row.get(key, "") for key in keys if has_value(row.get(key, ""))]
    if not available_values:
        return ""
    return str(sum(to_int(value) for value in available_values))


def data_quality(row: dict[str, str]) -> str:
    has_content = has_value(row.get("post_text", ""))
    has_metrics = has_value(row.get("total_engagements", ""))
    if has_content and has_metrics:
        return "complete"
    if has_content:
        return "content_only"
    if has_metrics:
        return "metrics_only"
    return "url_only"


def platform_specific_data_quality(row: dict[str, str]) -> str:
    if row.get("platform") == "instagram" and row.get("author_handle") not in {"", "goodsuniteus"}:
        return "out_of_scope"
    if row.get("platform") == "instagram":
        return data_quality(row)
    if row.get("platform") == "threads":
        return data_quality(row)
    if row.get("platform") == "bluesky" and has_value(row.get("total_engagements", "")):
        return "complete"
    return data_quality(row)


def percentile_ranks(rows: list[dict[str, str]]) -> None:
    by_platform: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_platform[row.get("platform", "")].append(row)

    for platform_rows in by_platform.values():
        ranked_rows = [row for row in platform_rows if has_value(row.get("total_engagements", ""))]
        sorted_scores = sorted(to_int(row["total_engagements"]) for row in ranked_rows)
        n = len(sorted_scores)
        if n == 0:
            for row in platform_rows:
                row["platform_percentile"] = ""
            continue
        if n <= 1:
            for row in ranked_rows:
                row["platform_percentile"] = "100"
            for row in platform_rows:
                row.setdefault("platform_percentile", "")
            continue
        for row in ranked_rows:
            score = to_int(row["total_engagements"])
            below_or_equal = sum(1 for value in sorted_scores if value <= score)
            row["platform_percentile"] = f"{100 * (below_or_equal - 1) / (n - 1):.1f}"
        for row in platform_rows:
            if not has_value(row.get("total_engagements", "")):
                row["platform_percentile"] = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build enriched social_posts_raw master CSV.")
    parser.add_argument("--input", type=Path, nargs="+", action="append", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for paths in args.input:
        for path in paths:
            for row in read_rows(path):
                key = (row.get("platform", ""), row.get("post_url", "") or row.get("post_id", ""))
                if key in seen:
                    continue
                seen.add(key)
                normalized = {field: row.get(field, "") for field in FIELDS}
                normalized["total_engagements"] = engagement(normalized)
                normalized["data_quality"] = platform_specific_data_quality(normalized)
                merged.append(normalized)

    percentile_ranks(merged)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged)

    print(f"Wrote {len(merged)} rows to {args.output_csv}")


if __name__ == "__main__":
    main()
