from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


BASE_FIELDS = [
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

CLASSIFICATION_FIELDS = [
    "topic",
    "content_type",
    "hook_type",
    "tone",
    "cta_type",
    "post_length_chars",
    "post_length_words",
    "question_present",
    "hashtag_count",
    "link_present",
    "image_present",
    "performance_band",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def numeric(value: str) -> float | None:
    try:
        if value == "" or value is None:
            return None
        return float(value)
    except ValueError:
        return None


def classify_topic(text: str) -> str:
    lower = text.lower()
    if "gave $" in lower or "donation" in lower or "pac" in lower:
        return "political_donations"
    if "where " in lower and " stands on " in lower:
        return "politician_issue_position"
    if "how " in lower and " feels about " in lower:
        return "company_issue_position"
    if "vote with your wallet" in lower:
        return "consumer_action"
    if "app" in lower or "download" in lower:
        return "app_promotion"
    if any(term in lower for term in ["abortion", "dei", "gun control", "minimum wage", "lgbtq", "healthcare", "israel", "immigrant"]):
        return "issue_position"
    return "general_brand"


def classify_content_type(text: str, media_type: str) -> str:
    lower = text.lower()
    if lower.startswith("breaking:"):
        return "breaking_donation_alert"
    if "full breakdown" in lower:
        return "issue_breakdown"
    if "see where" in lower and "stands on" in lower:
        return "politician_card"
    if "see how" in lower and "feels about" in lower:
        return "company_card"
    if "download the free app" in lower or "download the goods app" in lower:
        return "app_download_prompt"
    if media_type == "image":
        return "image_post"
    return "text_post"


def classify_hook(text: str) -> str:
    lower = text.lower().strip()
    if lower.startswith("breaking:"):
        return "breaking_news"
    if lower.startswith("see how"):
        return "see_how"
    if lower.startswith("see where"):
        return "see_where"
    if lower.startswith("vote with your wallet"):
        return "imperative"
    if "?" in text:
        return "question"
    if lower.startswith("#"):
        return "hashtag_first"
    return "statement"


def classify_tone(text: str) -> str:
    lower = text.lower()
    if lower.startswith("breaking:"):
        return "urgent"
    if "download" in lower or "link in bio" in lower:
        return "promotional"
    if "see how" in lower or "see where" in lower:
        return "informational"
    if "vote with your wallet" in lower:
        return "mobilizing"
    return "neutral"


def classify_cta(text: str) -> str:
    lower = text.lower()
    if "download the free app" in lower:
        return "download_free_app"
    if "download the goods app" in lower:
        return "download_goods_app"
    if "link in bio" in lower:
        return "link_in_bio"
    if "full breakdown" in lower:
        return "full_breakdown"
    if "see where" in lower or "see how" in lower:
        return "learn_more"
    if "vote with your wallet" in lower:
        return "vote_with_wallet"
    if "https://" in lower or "http://" in lower:
        return "external_link"
    return "none"


def performance_band(percentile: str) -> str:
    value = numeric(percentile)
    if value is None:
        return ""
    if value >= 75:
        return "top_quartile"
    if value >= 50:
        return "upper_middle"
    if value >= 25:
        return "lower_middle"
    return "bottom_quartile"


def enrich(row: dict[str, str]) -> dict[str, str]:
    enriched = dict(row)
    text = row.get("post_text", "")
    words = re.findall(r"\b[\w'-]+\b", text)
    hashtags = re.findall(r"#[\w]+", text)
    enriched.update(
        {
            "topic": classify_topic(text),
            "content_type": classify_content_type(text, row.get("media_type", "")),
            "hook_type": classify_hook(text),
            "tone": classify_tone(text),
            "cta_type": classify_cta(text),
            "post_length_chars": str(len(text)),
            "post_length_words": str(len(words)),
            "question_present": "true" if "?" in text else "false",
            "hashtag_count": str(len(hashtags)),
            "link_present": "true" if re.search(r"https?://", text) else "false",
            "image_present": "true" if row.get("image_url") else "false",
            "performance_band": performance_band(row.get("platform_percentile", "")),
        }
    )
    return enriched


def grouped_summary(rows: list[dict[str, str]], group_fields: list[str]) -> list[dict[str, str]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not row.get("total_engagements"):
            continue
        groups[tuple(row.get(field, "") for field in group_fields)].append(row)

    output: list[dict[str, str]] = []
    for key, group_rows in sorted(groups.items()):
        engagements = [numeric(row["total_engagements"]) or 0 for row in group_rows]
        percentiles = [numeric(row["platform_percentile"]) for row in group_rows if numeric(row["platform_percentile"]) is not None]
        output.append(
            {
                **{field: key[index] for index, field in enumerate(group_fields)},
                "post_count": str(len(group_rows)),
                "avg_total_engagements": f"{mean(engagements):.1f}",
                "median_total_engagements": f"{median(engagements):.1f}",
                "avg_platform_percentile": f"{mean(percentiles):.1f}" if percentiles else "",
                "top_quartile_posts": str(sum(row.get("performance_band") == "top_quartile" for row in group_rows)),
            }
        )
    return output


def top_posts(rows: list[dict[str, str]], platform: str, limit: int = 5) -> list[dict[str, str]]:
    candidates = [
        row
        for row in rows
        if row.get("platform") == platform
        and row.get("data_quality") == "complete"
        and row.get("total_engagements")
    ]
    return sorted(
        candidates,
        key=lambda row: (numeric(row.get("platform_percentile", "")) or -1, numeric(row.get("total_engagements", "")) or -1),
        reverse=True,
    )[:limit]


def make_markdown(rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> str:
    platform_counts = Counter(row.get("platform", "") for row in rows)
    quality_counts = Counter((row.get("platform", ""), row.get("data_quality", "")) for row in rows)
    complete_rows = [row for row in rows if row.get("data_quality") == "complete"]
    topic_counts = Counter(row.get("topic", "") for row in complete_rows)
    content_counts = Counter(row.get("content_type", "") for row in complete_rows)

    lines = [
        "# Social Content Analysis",
        "",
        "## Dataset status",
        "",
        f"- Total rows: {len(rows)}",
        f"- Platform counts: {dict(platform_counts)}",
        f"- Data quality counts: {dict(quality_counts)}",
        "",
        "## First-pass findings",
        "",
        "- Bluesky is the strongest analysis base right now because it has the most complete public post and engagement data.",
        "- Instagram now has usable public post data for owned Goods Unite Us posts, but still lacks private metrics such as reach, saves and shares.",
        "- Threads has text/content only from scraping; meaningful performance analysis should wait for Threads Insights/API export.",
        "- Percentiles are platform-relative, which avoids treating small-network and larger-network raw engagement as directly equivalent.",
        "",
        "## Content mix among complete rows",
        "",
        f"- Topics: {dict(topic_counts.most_common())}",
        f"- Content types: {dict(content_counts.most_common())}",
        "",
        "## Top posts by platform-relative percentile",
        "",
    ]

    for platform in sorted(platform_counts):
        posts = top_posts(rows, platform)
        if not posts:
            continue
        lines.append(f"### {platform.title()}")
        for post in posts:
            text = post.get("post_text", "").replace("\n", " ")
            if len(text) > 180:
                text = text[:177] + "..."
            lines.append(
                f"- {post.get('platform_percentile', '')} percentile, "
                f"{post.get('total_engagements', '')} engagements, "
                f"{post.get('content_type', '')}: {text}"
            )
        lines.append("")

    lines.extend(
        [
            "## Recommendations",
            "",
            "1. Treat this as a public-content pilot, not the final six-month analytics dataset.",
            "2. Get Meta/Threads owned-account exports or API access for reach, saves, shares and views.",
            "3. Use the enriched CSV to run LLM review on post language once owned metrics are joined.",
            "4. Keep Bluesky API collection as the reliable baseline and schedule it for regular refreshes.",
            "5. Use Instagram scraping only as a fallback for public captions, dates and visible engagement.",
            "",
            "## Analysis table",
            "",
            "| Platform | Group | Posts | Avg engagements | Avg percentile | Top quartile posts |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary_rows:
        lines.append(
            f"| {row.get('platform', '')} | {row.get('content_type', '')} | "
            f"{row.get('post_count', '')} | {row.get('avg_total_engagements', '')} | "
            f"{row.get('avg_platform_percentile', '')} | {row.get('top_quartile_posts', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich and summarize normalized social post data.")
    parser.add_argument("--input", type=Path, default=Path("decodo_travel_scraper/outputs/social_posts_master.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/analysis"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [enrich(row) for row in read_rows(args.input)]
    fields = BASE_FIELDS + CLASSIFICATION_FIELDS
    enriched_path = args.output_dir / "social_posts_enriched.csv"
    summary_path = args.output_dir / "platform_content_performance.csv"
    markdown_path = args.output_dir / "social_analysis_summary.md"

    write_csv(enriched_path, rows, fields)
    summary_rows = grouped_summary(rows, ["platform", "content_type"])
    write_csv(
        summary_path,
        summary_rows,
        ["platform", "content_type", "post_count", "avg_total_engagements", "median_total_engagements", "avg_platform_percentile", "top_quartile_posts"],
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(make_markdown(rows, summary_rows), encoding="utf-8")
    print(f"Wrote enriched posts to {enriched_path}")
    print(f"Wrote performance summary to {summary_path}")
    print(f"Wrote markdown analysis to {markdown_path}")


if __name__ == "__main__":
    main()
