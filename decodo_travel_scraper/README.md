# Decodo Scraper

Standalone Decodo scraper for permitted public pages.

## Setup

Set your Decodo credentials:

```bash
export DECODO_USERNAME="your_username"
export DECODO_PASSWORD="your_password"
```

Or use a pre-encoded Basic token:

```bash
export DECODO_AUTH="your_basic_auth_token"
```

## Add URLs

Edit `travel_urls.txt` and replace the placeholder URLs with permitted public pages.

## Run

From this folder:

```bash
python3 scrape_travel.py --url-file travel_urls.txt
```

From the project root:

```bash
python3 decodo_travel_scraper/scrape_travel.py \
  --url-file decodo_travel_scraper/travel_urls.txt \
  --output-dir decodo_travel_scraper/outputs
```

## Output

The script writes CSV and JSONL files to `outputs/`.

CSV columns:

```text
url
status
title
meta_description
price_snippets
rating_snippets
date_snippets
travel_terms
visible_text_preview
raw
collected_at
```

## Social audit next steps

Rebuild the normalized master file after parsing post-level scrapes:

```bash
python3 decodo_travel_scraper/build_master_social_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_raw.csv \
  --input decodo_travel_scraper/outputs/instagram_threads_posts.csv \
  --output-csv decodo_travel_scraper/outputs/social_posts_master.csv
```

Test exactly one Instagram post with JavaScript rendering and browser actions before spending requests on all 12 discovered Instagram URLs:

```bash
python3 decodo_travel_scraper/test_instagram_rendered_post.py
```

By default this uses the first URL in `outputs/post_scrapes/instagram_urls.txt`, waits for rendering, scrolls once, and writes one result under `outputs/instagram_rendered_tests/`.

If the one-post test captures the caption and image, scrape the 12 known Instagram post URLs with the same rendered Markdown setup:

```bash
python3 decodo_travel_scraper/scrape_post_urls.py \
  --post-urls-csv decodo_travel_scraper/outputs/travel_pages_20260929T222511Z_post_urls.csv \
  --platform instagram \
  --output-dir decodo_travel_scraper/outputs/post_scrapes_instagram_rendered \
  --proxy-pool premium \
  --markdown \
  --xhr \
  --browser-actions-json decodo_travel_scraper/instagram_rendered_actions.json
```

Then parse the latest rendered Instagram JSONL together with the existing Threads JSONL:

```bash
python3 decodo_travel_scraper/parse_individual_post_scrapes.py \
  decodo_travel_scraper/outputs/post_scrapes_instagram_rendered/instagram_posts_*.jsonl \
  decodo_travel_scraper/outputs/post_scrapes/threads_posts_20260929T235332Z.jsonl \
  --output-csv decodo_travel_scraper/outputs/instagram_threads_posts.csv
```

Finally rebuild the master:

```bash
python3 decodo_travel_scraper/build_master_social_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_raw.csv \
  --input decodo_travel_scraper/outputs/instagram_threads_posts.csv \
  --output-csv decodo_travel_scraper/outputs/social_posts_master.csv
```

## Local Chromium renderer

For a local browser-rendering alternative to Decodo, install Selenium and BeautifulSoup:

```bash
python3 -m pip install -r decodo_travel_scraper/requirements_browser.txt
```

Render one page with Chrome/Chromium and parse the rendered HTML:

```bash
python3 decodo_travel_scraper/selenium_chromium_scraper.py \
  --url https://www.instagram.com/goodsuniteus/?hl=en \
  --output-dir decodo_travel_scraper/outputs/selenium_chromium \
  --screenshot
```

Render a file of URLs:

```bash
python3 decodo_travel_scraper/selenium_chromium_scraper.py \
  --url-file decodo_travel_scraper/outputs/post_scrapes/instagram_urls.txt \
  --output-dir decodo_travel_scraper/outputs/selenium_chromium \
  --wait-seconds 8 \
  --scrolls 2 \
  --screenshot
```

This writes CSV, JSONL, rendered HTML files, and optional screenshots. Use it only for pages you are permitted to access. For owned-account analytics, prefer official exports/APIs.

## Meta and Threads APIs

Use these scripts when Goods Unite Us can provide owned-account API access. This is the right path for metrics that scraping cannot reliably capture, such as reach, saves, shares, views and Threads repost/quote counts.

Add these values to `decodo_travel_scraper/.env`:

```bash
META_ACCESS_TOKEN=your_meta_graph_api_token
INSTAGRAM_USER_ID=your_instagram_business_or_creator_user_id

THREADS_ACCESS_TOKEN=your_threads_api_token
THREADS_USER_ID=your_threads_user_id
```

Instagram owned media and insights:

```bash
python3 decodo_travel_scraper/fetch_meta_instagram_insights.py \
  --limit 100 \
  --output-dir decodo_travel_scraper/outputs/meta_api
```

Threads owned posts and insights:

```bash
python3 decodo_travel_scraper/fetch_meta_threads_insights.py \
  --limit 100 \
  --output-dir decodo_travel_scraper/outputs/meta_api
```

Rebuild the master using API outputs first so they override scrape-only rows for the same platform/post URLs:

```bash
python3 decodo_travel_scraper/build_master_social_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_raw.csv \
  --input decodo_travel_scraper/outputs/meta_api/meta_instagram_posts_*.csv \
  --input decodo_travel_scraper/outputs/meta_api/meta_threads_posts_*.csv \
  --input decodo_travel_scraper/outputs/instagram_threads_posts.csv \
  --output-csv decodo_travel_scraper/outputs/social_posts_master.csv
```

Then rerun the analysis:

```bash
python3 decodo_travel_scraper/analyze_social_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/analysis
```

## LLM classification

To test the LLM classification file flow without API calls:

```bash
python3 decodo_travel_scraper/llm_classify_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/llm \
  --include-content-only \
  --limit 10 \
  --dry-run
```

To run true OpenAI LLM classification, add an API key to `decodo_travel_scraper/.env`:

```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Then run:

```bash
python3 decodo_travel_scraper/llm_classify_posts.py \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/llm \
  --include-content-only
```

This writes:

- `outputs/llm/llm_annotations.csv`
- `outputs/llm/social_posts_llm_classified.csv`

If OpenAI API credits are unavailable, use local Ollama instead:

```bash
brew install ollama
ollama serve
```

In a second terminal:

```bash
ollama pull llama3.1:8b
```

Then run local LLM classification:

```bash
python3 decodo_travel_scraper/llm_classify_posts.py \
  --provider ollama \
  --ollama-model llama3.1:8b \
  --input decodo_travel_scraper/outputs/social_posts_master.csv \
  --output-dir decodo_travel_scraper/outputs/llm \
  --include-content-only
```

Summarize the LLM annotations:

```bash
python3 decodo_travel_scraper/summarize_llm_annotations.py \
  --input decodo_travel_scraper/outputs/llm/social_posts_llm_classified.csv \
  --output-dir decodo_travel_scraper/outputs/llm
```

## Dashboard

Install the dashboard dependencies inside the project virtual environment:

```bash
source .venv/bin/activate
python -m pip install -r decodo_travel_scraper/requirements_dashboard.txt
```

Run the Streamlit dashboard:

```bash
streamlit run decodo_travel_scraper/social_dashboard.py
```

The dashboard automatically uses the richest available file in this order:

- `outputs/llm/social_posts_llm_classified.csv`
- `outputs/analysis/social_posts_enriched.csv`
- `outputs/social_posts_master.csv`

## Looker Studio export

Build Looker Studio friendly CSV tables from the LLM-classified post dataset:

```bash
python3 decodo_travel_scraper/build_looker_studio_exports.py
```

This writes:

- `outputs/looker_studio/social_posts_looker.csv`
- `outputs/looker_studio/platform_summary.csv`
- `outputs/looker_studio/content_lane_summary.csv`
- `outputs/looker_studio/emotional_frame_summary.csv`
- `outputs/looker_studio/monthly_platform_summary.csv`
- `outputs/looker_studio/creative_review_queue.csv`
- `outputs/looker_studio/data_dictionary.csv`
- `outputs/looker_studio/looker_studio_report_blueprint.md`

Recommended setup:

1. Upload `social_posts_looker.csv` to Google Sheets or BigQuery.
2. Create a Looker Studio report using that sheet/table as the primary data source.
3. Use `looker_studio_report_blueprint.md` for report pages, chart choices, filters, and calculated fields.
4. Keep the aggregate CSVs available as optional supporting data sources for faster summary charts.

Relevant official docs:

- Instagram media insights: https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights/
- Instagram user media: https://developers.facebook.com/docs/instagram-platform/reference/instagram-user/media/
- Threads insights: https://developers.facebook.com/docs/threads/insights/

## Notes

- Use this only for public pages where scraping is permitted.
- For sites with official APIs, prefer the API.
- Keep Decodo credentials out of git and do not paste them into files committed to source control.
