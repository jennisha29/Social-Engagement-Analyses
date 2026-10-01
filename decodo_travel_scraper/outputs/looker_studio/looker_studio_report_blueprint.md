# Looker Studio Report Blueprint

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
