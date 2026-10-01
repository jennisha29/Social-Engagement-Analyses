# Technical Implementation Plan

## Objective

Build a repeatable Social Content Intelligence pipeline for Goods Unite Us that combines platform analytics, public post content, LLM annotations, media review, and dashboard reporting. The system should answer:

- Which posts work on each platform?
- Which formats, hooks, topics, CTAs, and visuals correlate with stronger performance?
- Which posts should be repurposed, revised, or retired?
- What should the next test backlog look like?

## Current State

We already have a working public-data pilot:

- `social_posts_master.csv`: normalized post-level dataset.
- `social_posts_enriched.csv`: rule-based content classification and performance bands.
- `social_analysis_summary.md`: first-pass quantitative summary.
- `manual_post_review.md`: qualitative review and recommendations.
- Decodo scripts for public scraping.
- Selenium + BeautifulSoup local browser-rendering fallback.
- Meta/Threads API scripts prepared for owned analytics once credentials are available.

Current dataset status:

| Platform | Status |
| --- | --- |
| Bluesky | 97 complete public posts via public API |
| Instagram | 11 complete owned public-visible posts, 1 out-of-scope post |
| Threads | 4 content-only posts |
| X/Twitter | URLs discovered, API/native export still needed |
| TikTok | Not collected yet |

This is enough for an exploratory public-content audit, but not enough for final owned-analytics conclusions because we do not yet have reach, impressions, saves, shares, profile actions, follower growth, or video retention.

## Phase 1: Data Collection

### Canonical Table: `social_posts`

Create one canonical post-level table. This table should include both public content fields and owned analytics fields.

| Field | Description |
| --- | --- |
| `post_id` | Internal UUID or stable warehouse key |
| `platform` | Instagram, Threads, Bluesky, X, TikTok |
| `platform_post_id` | Native platform ID or shortcode |
| `post_url` | Public URL where available |
| `published_at` | Native publish timestamp |
| `caption_text` | Caption/body text |
| `media_type` | text, image, video, carousel, reel, etc. |
| `media_urls` | One or more archived media URLs |
| `hashtags` | Extracted hashtags |
| `mentions` | Extracted mentions |
| `link_url` | Primary outbound URL |
| `campaign` | Optional campaign label |
| `topic` | Human/LLM topic label |
| `cta` | Primary call to action |
| `impressions` | Native impressions where available |
| `views` | Native views/video views where available |
| `likes` | Likes/favorites |
| `comments` | Instagram/TikTok comments |
| `replies` | Threads/Bluesky/X replies |
| `shares` | Shares where available |
| `reposts` | Reposts/retweets/reblogs |
| `quotes` | Quote posts |
| `saves` | Instagram/TikTok saves where available |
| `bookmarks` | X bookmarks where available |
| `clicks` | Link clicks where available |
| `profile_visits` | Profile visits from post where available |
| `follows` | Follows attributed to post where available |
| `watch_time` | Video watch time where available |
| `completion_rate` | Video completion rate where available |
| `follower_count_at_post_time` | Follower count snapshot near publish time |

### Canonical Table: `llm_annotations`

Create a second table for descriptive AI/manual labels. Keep this separate so annotations can be rerun without rewriting source metrics.

| Field | Description |
| --- | --- |
| `post_id` | Foreign key to `social_posts` |
| `content_lane` | Brand education, company callout, politician card, donation alert, app education, etc. |
| `topic` | Main subject matter |
| `emotional_frame` | Informational, urgent, surprising, values-based, accountability, practical |
| `audience` | Likely intended audience segment |
| `cta_type` | Download app, link in bio, learn more, discuss, share, no CTA |
| `clarity_score` | 1-5 descriptive score |
| `shareability_score` | 1-5 descriptive score |
| `risk_score` | 1-5 brand/reputational or ambiguity risk score |
| `visual_score` | 1-5 visual clarity/usefulness score |
| `summary` | One-sentence summary of what the post is doing |
| `failure_reason` | Why the post may underperform |
| `repurpose_recommendation` | Suggested platform/format reuse |

### Initial Data Sources

| Source | Current Role | Future Role |
| --- | --- | --- |
| Bluesky public API | Working source for public posts and engagement | Continue as reliable baseline |
| Instagram public scrape | Captions, images, visible likes/comments | Fallback for public content |
| Threads public scrape | Text/content only | Fallback for content |
| Meta Instagram API | Prepared, awaiting credentials | Owned metrics: reach, views, saves, shares, interactions |
| Threads API | Prepared, awaiting credentials | Owned metrics: views, likes, replies, reposts, quotes, shares |
| X API/export | Not implemented yet | Impressions, bookmarks, engagements, link clicks |
| TikTok export/API | Not implemented yet | Views, likes, comments, shares, saves, retention |
| Native analytics exports | Not collected yet | Fastest path if API access is delayed |

## Phase 2: Pipeline

### Recommended Stack

| Layer | Tooling |
| --- | --- |
| Ingestion | Python, Airbyte/custom API jobs, scheduled cron or GitHub Actions |
| Storage | Postgres for fast setup, BigQuery for larger warehouse use |
| Media archive | S3, GCS, or local object storage during pilot |
| LLM processing | OpenAI batch jobs for text and vision annotations |
| Transformations | dbt for warehouse transforms, Python notebooks for pilot analysis |
| Dashboard | Streamlit for pilot, Metabase/Looker Studio/Superset for shared BI |
| Experiment tracker | Simple database table first, later Optimizely-like workflow |

### Ingestion Flow

```text
Platform API / native export / approved scraper
        ↓
Raw JSON/CSV archive
        ↓
Normalize into social_posts
        ↓
Archive media and screenshots where allowed
        ↓
LLM/manual annotation into llm_annotations
        ↓
Performance scoring + dashboard tables
        ↓
Strategy memo / dashboard / experiment backlog
```

### Current Scripts

| Script | Purpose |
| --- | --- |
| `scrape_travel.py` | Decodo scrape wrapper |
| `extract_post_urls.py` | Extract social post URLs from scraped profiles |
| `scrape_post_urls.py` | Scrape individual Instagram/Threads URLs |
| `parse_individual_post_scrapes.py` | Normalize Instagram/Threads public scrape results |
| `bluesky_to_social_posts_raw.py` | Convert Bluesky API data into master schema |
| `build_master_social_posts.py` | Merge normalized sources and calculate engagement/percentiles |
| `analyze_social_posts.py` | Rule-based enrichment and summary outputs |
| `selenium_chromium_scraper.py` | Local Selenium + BeautifulSoup renderer/parser |
| `fetch_meta_instagram_insights.py` | Prepared Instagram Graph API collector |
| `fetch_meta_threads_insights.py` | Prepared Threads API collector |
| `llm_classify_posts.py` | OpenAI-powered descriptive post annotation with dry-run mode |

### LLM Processing Workflow

Use a two-stage annotation process:

1. **Text annotation**
   - Input: caption/body text, platform, media type, visible metrics.
   - Output: content lane, topic, hook, tone, CTA, clarity, shareability, failure reason.

2. **Visual annotation**
   - Input: image URL or archived screenshot/media.
   - Output: visual type, text overlay, screenshot/app UI detection, complexity, visual score.

Recommended controls:

- Store prompt version on each annotation row.
- Store model name and run timestamp.
- Keep raw LLM JSON output for audit/debugging.
- Do not optimize for political persuasion; keep labels descriptive and performance-observational.

Current implementation:

```bash
python3 decodo_travel_scraper/llm_classify_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/llm \
  --include-content-only
```

Use `--dry-run` to validate the file flow without API calls.

OpenAI API credits were unavailable during the pilot, so local LLM classification was completed with Ollama:

```bash
python3 decodo_travel_scraper/llm_classify_posts.py \
  --provider ollama \
  --ollama-model llama3.1:8b \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/llm \
  --include-content-only
```

Outputs:

- `outputs/llm/llm_annotations.csv`
- `outputs/llm/social_posts_llm_classified.csv`
- `outputs/llm/llm_annotation_summary.md`

### Normalized Scoring

Use platform-relative scoring instead of raw engagement comparisons.

Recommended derived metrics:

| Metric | Definition |
| --- | --- |
| `total_engagements` | Platform-appropriate sum of likes/comments/replies/shares/reposts/quotes/saves |
| `platform_percentile` | Percentile within the same platform |
| `engagement_rate` | Engagements / followers at post time |
| `save_share_rate` | Saves + shares / impressions or reach |
| `conversation_rate` | Replies/comments / impressions or reach |
| `amplification_rate` | Reposts + shares + quotes / impressions or reach |
| `click_rate` | Link clicks / impressions or reach |
| `retention_score` | Watch time/completion for video |

## Phase 3: Dashboard Design

### Tab 1: Overview

Purpose: quick health snapshot.

Widgets:

- Total posts
- Engagement index
- Follower growth
- Best/worst platforms
- Top content lanes
- Recent top posts
- Data completeness by platform

### Tab 2: Platform Comparison

Purpose: compare what works where without overvaluing raw engagement from one network.

Views:

- Normalized performance by platform
- Format performance by platform
- Best posting days/times
- Link/click performance
- Engagement mix by platform
- Metric availability/data quality warnings

### Tab 3: Content Intelligence

Purpose: connect language and topic patterns to outcomes.

Views:

- Top themes
- Emotional frames that work
- CTA performance
- Brand/company mentions that overperform
- Posts with high saves/shares versus high comments
- Hook style by platform
- Topic performance trends

### Tab 4: Creative Review

Purpose: improve copy and visuals.

Views:

- Top visual patterns
- Weak visuals
- High-performing copy hooks
- Repurposing recommendations
- Image/text-overlay review
- Manual reviewer notes

### Tab 5: Experiment Backlog

Purpose: move from analysis to testing.

Fields:

- Hypothesis
- Generated variants
- Target platform
- Expected metric
- Result
- Status
- Owner
- Launch date
- Notes

## Platform Recommendations

### Instagram

Use Instagram for visual proof, carousels, app education, and “buy this/not that” comparisons. Prioritize saves and shares, not just likes. Best formats to test:

- Carousels explaining one company/issue relationship.
- Reels showing app use.
- Brand comparison graphics.
- Broad app-value posts explaining why Goods Unite Us matters.

Current pilot signal: broader app/value posts performed better than repeated issue-card captions in the small visible sample.

### Threads

Use Threads for conversational, values-based posts. Test:

- Short opinionated posts.
- Questions.
- News reactions.
- Warmer rewrites of strong X/Bluesky text posts.

Current limitation: Threads scraping produced content only, not performance metrics. Use Threads Insights/API before making performance claims.

### Bluesky

Use Bluesky for sharper commentary, journalist/political-audience discovery, and repostable data points. Since impressions may be limited, judge success by:

- Repost/reply/like ratios.
- Follower growth.
- Which data points get amplified.

Current pilot signal: image posts and feed-native text/commentary outperform many repeated company/politician card formats.

### X/Twitter

Use X for breaking news, public figures, company callouts, and rapid-response posts. Track:

- Impressions.
- Bookmarks.
- Link clicks.
- Reposts/quotes.

Be mindful of API access limits and cost. Use authorized exports/API access instead of scraping whenever possible.

### TikTok

Only pursue TikTok if Goods Unite Us can make native short-form video, not just repurposed graphics. Strong concepts:

- “I searched the brand before buying.”
- “3 brands that surprised us.”
- “What your grocery cart funds.”
- Comment-response videos.
- Screen-recorded app walkthroughs with a human explanation.

Prioritize watch time, completion rate, saves, shares, and comments.

## 90-Day Pilot

| Timeframe | Work |
| --- | --- |
| Weeks 1-2 | Export/API pull last 6-12 months of posts and metrics |
| Weeks 3-4 | LLM labeling, visual review, normalized scoring |
| Weeks 5-6 | Identify winning/losing patterns and platform differences |
| Weeks 7-10 | Generate and publish structured test variants |
| Weeks 11-12 | Analyze results and create repeatable content playbook |

## Final Deliverable

The useful final artifact should be a living Social Content Intelligence report with:

- Top 10 winning post patterns.
- Top 10 underperforming patterns.
- Platform-by-platform content rules.
- Reusable LLM prompts.
- Experiment backlog.
- Dashboard.
- Monthly recommendation cycle.

## Immediate Next Steps

1. Keep the current public-content pilot as the first exploratory dataset.
2. Request Meta/Threads/X/TikTok native analytics access or exports.
3. Add true LLM classification script and store outputs in `llm_annotations`.
4. Build a simple Streamlit dashboard from `social_posts_enriched.csv`.
5. Convert this plan and the manual review into the exploratory strategy memo.
