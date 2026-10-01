from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "outputs" / "llm" / "social_posts_llm_classified.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "looker_studio"

NUMERIC_COLS = [
    "likes",
    "comments",
    "replies",
    "shares",
    "reposts",
    "quotes",
    "total_engagements",
    "platform_percentile",
    "llm_clarity_score",
    "llm_shareability_score",
    "llm_risk_score",
    "llm_visual_score",
    "llm_confidence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Google Looker Studio friendly CSV exports from classified social posts."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def clean_text(value: object, max_len: int = 500) -> str:
    if pd.isna(value):
        return ""
    text = " ".join(str(value).split())
    if len(text) > max_len:
        return text[: max_len - 3].rstrip() + "..."
    return text


def performance_band(percentile: float | None) -> str:
    if pd.isna(percentile):
        return "no metric"
    if percentile >= 90:
        return "top 10%"
    if percentile >= 75:
        return "strong"
    if percentile >= 50:
        return "middle"
    if percentile >= 25:
        return "soft"
    return "low"


def text_length_bucket(words: float | None) -> str:
    if pd.isna(words):
        return "unknown"
    if words <= 20:
        return "short"
    if words <= 60:
        return "medium"
    return "long"


def media_bucket(row: pd.Series) -> str:
    media_type = clean_text(row.get("media_type", ""), 80).lower()
    image_url = clean_text(row.get("image_url", ""), 200)
    if media_type:
        return media_type
    if image_url:
        return "image"
    return "text_only"


def normalize_posts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "published_at" in df.columns:
        published = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    else:
        published = pd.Series(pd.NaT, index=df.index)

    now = pd.Timestamp.now(tz="UTC").normalize()
    df["published_date"] = published.dt.date.astype("string").fillna("")
    df["published_month"] = published.dt.strftime("%Y-%m").fillna("")
    df["published_year"] = published.dt.year.astype("Int64").astype("string").replace("<NA>", "")
    df["published_weekday"] = published.dt.day_name().fillna("")
    df["published_hour_utc"] = published.dt.hour.astype("Int64").astype("string").replace("<NA>", "")
    df["post_age_days"] = (now - published.dt.normalize()).dt.days

    post_text = df["post_text"] if "post_text" in df.columns else pd.Series("", index=df.index)
    df["caption_preview"] = post_text.apply(lambda value: clean_text(value, 500))
    df["caption_word_count"] = post_text.fillna("").astype(str).str.split().str.len()
    df["caption_length_bucket"] = df["caption_word_count"].apply(text_length_bucket)

    df["metric_available"] = df["total_engagements"].notna() if "total_engagements" in df.columns else False
    df["performance_band"] = df.get("platform_percentile", pd.Series(pd.NA, index=df.index)).apply(performance_band)
    df["media_bucket"] = df.apply(media_bucket, axis=1)
    df["has_image"] = df.get("image_url", pd.Series("", index=df.index)).fillna("").astype(str).ne("")
    df["has_link"] = df["caption_preview"].str.contains("http|www\\.", case=False, regex=True, na=False)
    df["post_key"] = df.get("platform", "").astype(str) + ":" + df.get("post_id", "").astype(str)

    rename_map = {
        "llm_content_lane": "content_lane",
        "llm_topic": "topic",
        "llm_emotional_frame": "emotional_frame",
        "llm_audience": "audience",
        "llm_cta_type": "cta_type",
        "llm_clarity_score": "clarity_score",
        "llm_shareability_score": "shareability_score",
        "llm_risk_score": "risk_score",
        "llm_visual_score": "visual_score",
        "llm_summary": "llm_summary",
        "llm_failure_reason": "failure_reason",
        "llm_repurpose_recommendation": "repurpose_recommendation",
        "llm_confidence": "llm_confidence",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    ordered_cols = [
        "post_key",
        "platform",
        "author_handle",
        "post_id",
        "threads_internal_id",
        "post_url",
        "published_at",
        "published_date",
        "published_month",
        "published_year",
        "published_weekday",
        "published_hour_utc",
        "post_age_days",
        "caption_preview",
        "caption_word_count",
        "caption_length_bucket",
        "media_type",
        "media_bucket",
        "has_image",
        "has_link",
        "image_url",
        "data_quality",
        "metric_available",
        "likes",
        "comments",
        "replies",
        "shares",
        "reposts",
        "quotes",
        "total_engagements",
        "platform_percentile",
        "performance_band",
        "content_lane",
        "topic",
        "emotional_frame",
        "audience",
        "cta_type",
        "clarity_score",
        "shareability_score",
        "risk_score",
        "visual_score",
        "llm_confidence",
        "llm_summary",
        "failure_reason",
        "repurpose_recommendation",
        "scraped_at",
        "llm_classified_at",
        "llm_model",
    ]
    available = [col for col in ordered_cols if col in df.columns]
    return df[available].copy()


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    scored = df.copy()
    result = (
        scored.groupby(group_cols, dropna=False)
        .agg(
            posts=("post_key", "count"),
            posts_with_metrics=("metric_available", "sum"),
            total_engagements=("total_engagements", "sum"),
            avg_engagements=("total_engagements", "mean"),
            median_engagements=("total_engagements", "median"),
            avg_platform_percentile=("platform_percentile", "mean"),
            avg_clarity_score=("clarity_score", "mean"),
            avg_shareability_score=("shareability_score", "mean"),
            avg_visual_score=("visual_score", "mean"),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
    )
    numeric = result.select_dtypes(include="number").columns
    result[numeric] = result[numeric].round(2)
    return result.sort_values(group_cols).reset_index(drop=True)


def write_data_dictionary(output_dir: Path, posts: pd.DataFrame) -> None:
    descriptions = {
        "post_key": "Stable platform:post_id key for joins and row identity.",
        "platform": "Social platform.",
        "caption_preview": "Cleaned post text, truncated for reporting tables.",
        "metric_available": "True when at least one engagement metric exists.",
        "total_engagements": "Sum of available platform-appropriate engagement metrics.",
        "platform_percentile": "Within-platform performance percentile from 0 to 100.",
        "performance_band": "Human-readable band derived from platform_percentile.",
        "content_lane": "LLM descriptive content format classification.",
        "emotional_frame": "LLM descriptive emotional frame classification.",
        "cta_type": "LLM descriptive CTA classification.",
        "clarity_score": "LLM 1-5 clarity score.",
        "shareability_score": "LLM 1-5 shareability score.",
        "risk_score": "LLM 1-5 brand/compliance risk score.",
        "visual_score": "LLM 1-5 visual strength score where image context exists.",
    }
    rows = [
        {"field": col, "description": descriptions.get(col, ""), "looker_type_hint": type_hint(col)}
        for col in posts.columns
    ]
    pd.DataFrame(rows).fillna("").to_csv(output_dir / "data_dictionary.csv", index=False)


def type_hint(column: str) -> str:
    if column in {"published_at", "scraped_at", "llm_classified_at"}:
        return "Date & Time"
    if column in {"published_date"}:
        return "Date"
    if column in {"has_image", "has_link", "metric_available"}:
        return "Boolean"
    if column in NUMERIC_COLS or column in {
        "post_age_days",
        "caption_word_count",
        "clarity_score",
        "shareability_score",
        "risk_score",
        "visual_score",
    }:
        return "Number"
    return "Text"


def build_report_blueprint(output_dir: Path) -> None:
    text = """# Looker Studio Report Blueprint

## Data Source

Use `social_posts_looker.csv` as the primary data source. If you prefer Google Sheets, upload the CSV into a sheet first, then connect Looker Studio to that sheet.

Set these field types after connecting:

- `published_date`: Date
- `published_month`: Year Month or Text
- `metric_available`, `has_image`, `has_link`: Boolean
- `likes`, `comments`, `replies`, `shares`, `reposts`, `quotes`, `total_engagements`, `platform_percentile`: Number
- `clarity_score`, `shareability_score`, `risk_score`, `visual_score`, `llm_confidence`: Number

## Suggested Calculated Fields

`Posts`

```text
COUNT_DISTINCT(post_key)
```

`Posts With Metrics`

```text
SUM(CASE WHEN metric_available THEN 1 ELSE 0 END)
```

`Average Platform Percentile`

```text
AVG(platform_percentile)
```

`High Performing Posts`

```text
SUM(CASE WHEN platform_percentile >= 75 THEN 1 ELSE 0 END)
```

`Top 10 Percent Posts`

```text
SUM(CASE WHEN platform_percentile >= 90 THEN 1 ELSE 0 END)
```

`Metric Coverage Rate`

```text
Posts With Metrics / Posts
```

## Page 1: Overview

Scorecards:

- Posts
- Posts With Metrics
- Average Platform Percentile
- Total Engagements

Charts:

- Bar chart: Posts by platform
- Bar chart: Total engagements by platform
- Table: Top posts by platform_percentile with `platform`, `caption_preview`, `content_lane`, `performance_band`, `post_url`
- Donut chart: Data quality

Filters:

- Platform
- Data quality
- Published month
- Content lane

## Page 2: Platform Comparison

Charts:

- Bar chart: Average platform_percentile by platform
- Table: Platform summary by `platform`, `posts`, `posts_with_metrics`, `avg_platform_percentile`
- Stacked bar: Performance band by platform
- Time series: Posts by published_month and platform

Use `platform_summary.csv` if you want a pre-aggregated table for fast scorecards.

## Page 3: Content Intelligence

Charts:

- Bar chart: Average platform_percentile by content_lane
- Bar chart: Average platform_percentile by emotional_frame
- Bar chart: Average platform_percentile by cta_type
- Scatter: clarity_score vs shareability_score, colored by platform
- Table: content_lane_summary.csv

Main question:

Which content lanes, CTAs and emotional frames are associated with stronger within-platform performance?

## Page 4: Creative Review

Tables:

- Top posts: platform_percentile descending
- Weak posts: platform_percentile ascending
- High repurpose candidates: shareability_score >= 4 and platform_percentile >= 75
- Risk review: risk_score >= 4

Columns:

- platform
- caption_preview
- content_lane
- emotional_frame
- failure_reason
- repurpose_recommendation
- post_url

## Page 5: Data Quality

Charts:

- Table: data_quality by platform
- Scorecard: metric coverage rate
- Table: posts without metrics

Use this page to keep the limitations visible. Instagram and Threads should be treated as content-rich but metric-limited until owned-account exports or APIs are connected.
"""
    (output_dir / "looker_studio_report_blueprint.md").write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.input)
    posts = normalize_posts(raw)

    posts.to_csv(args.output_dir / "social_posts_looker.csv", index=False)
    summarize(posts, ["platform"]).to_csv(args.output_dir / "platform_summary.csv", index=False)
    summarize(posts, ["platform", "content_lane"]).to_csv(args.output_dir / "content_lane_summary.csv", index=False)
    summarize(posts, ["platform", "emotional_frame"]).to_csv(args.output_dir / "emotional_frame_summary.csv", index=False)
    summarize(posts, ["platform", "published_month"]).to_csv(args.output_dir / "monthly_platform_summary.csv", index=False)

    review_cols = [
        "platform",
        "post_key",
        "published_date",
        "caption_preview",
        "content_lane",
        "emotional_frame",
        "cta_type",
        "platform_percentile",
        "clarity_score",
        "shareability_score",
        "risk_score",
        "visual_score",
        "failure_reason",
        "repurpose_recommendation",
        "post_url",
    ]
    available_review_cols = [col for col in review_cols if col in posts.columns]
    posts[available_review_cols].to_csv(args.output_dir / "creative_review_queue.csv", index=False)

    write_data_dictionary(args.output_dir, posts)
    build_report_blueprint(args.output_dir)

    print(f"Wrote Looker Studio exports to {args.output_dir}")
    print(f"Rows: {len(posts)}")


if __name__ == "__main__":
    main()
