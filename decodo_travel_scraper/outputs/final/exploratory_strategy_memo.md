# Exploratory Strategy Memo

## Executive Summary

Goods Unite Us already has a strong social premise: help people understand the political and civic footprint of companies, brands, public figures, and spending decisions. The current content system is consistent and recognizable, but many posts read like app/database outputs rather than complete social posts.

The strongest early signal is that posts with a clear standalone takeaway perform better than posts that only ask users to click through. On Bluesky, image posts and feed-native text/commentary outperform many repeated company/politician card formats. On Instagram, the strongest visible post in our sample is a broader app/value-proposition post rather than a narrow issue-card post.

This should be treated as a public-visible exploratory audit, not a final owned-analytics report. We have enough data to identify early content patterns and create a testing roadmap. We do not yet have enough native analytics to make final conclusions about reach, saves, shares, impressions, profile visits, follows, link clicks, or video retention.

## Data Used

Current dataset:

| Platform | Status |
| --- | --- |
| Bluesky | 97 complete public posts |
| Instagram | 11 complete owned public-visible posts |
| Instagram | 1 out-of-scope post excluded from recommendations |
| Threads | 4 content-only posts |
| X/Twitter | URLs discovered, not yet analyzed with native metrics |
| TikTok | Not collected yet |

Source files:

- `social_posts_master.csv`
- `social_posts_enriched.csv`
- `llm_annotations.csv`
- `social_posts_llm_classified.csv`
- `llm_annotation_summary.md`
- `social_analysis_summary.md`
- `manual_post_review.md`

The dataset includes post text, dates, URLs, media type, image URLs where available, visible engagement metrics, platform-relative percentiles, and rule-based descriptive labels.

We also ran local LLM classification with Ollama `llama3.1:8b` across 112 usable rows: 97 Bluesky posts, 11 Instagram posts, and 4 Threads posts. The one out-of-scope Instagram row was excluded.

## What We Can Reliably Say

We can analyze:

- Public-visible engagement patterns.
- Relative performance within Bluesky and Instagram.
- Copy patterns, CTA structure, hashtags, topics, and post formats.
- Which public posts appear stronger or weaker within the collected sample.
- Manual reviewer impressions of clarity, feed-native value, and CTA friction.

We cannot yet reliably analyze:

- True reach or impressions.
- Saves and shares on Instagram.
- Profile visits or follows from posts.
- TikTok video retention.
- X bookmarks/impressions.
- Threads engagement rates.
- Six-month platform performance across all posts.

## Key Findings

### 1. The Current System Is Consistent, But Sometimes Too Template-Like

Many posts use repeatable structures:

- “See how [Company] feels about [Issue].”
- “See where [Politician] stands on [Issue].”
- “Download the free app to see more.”
- “Full breakdown / link in bio.”

This consistency is helpful for production, but the social output can feel repetitive. In lower-performing examples, the post feels like a lookup result rather than a complete feed-native message.

### 2. Feed-Native Posts Look Stronger

The posts that land better tend to deliver value before asking for a click. They include a clear claim, concrete fact, or memorable frame.

Examples of stronger directions:

- “Vote with your wallet.”
- “Now you know. Shop with purpose.”
- “We need campaign finance reform...yesterday.”
- “How the brands you buy affect our elections.”

These posts do not depend entirely on the app or link to create meaning.

### 3. Bluesky Rewards Simpler, More Direct Posts

Bluesky’s top visible performers include image posts and short text/commentary posts. Several high-performing examples are direct, punchy, or more human than the repeated card formats.

Pilot signal:

| Bluesky content type | Posts | Avg engagements | Avg percentile |
| --- | ---: | ---: | ---: |
| Image posts | 38 | 26.0 | 62.3 |
| Text posts | 29 | 23.7 | 67.8 |
| Company cards | 13 | 2.2 | 28.3 |
| Politician cards | 13 | 1.1 | 20.3 |
| Breaking donation alerts | 4 | 2.5 | 28.4 |

Interpretation: data-backed posts are valuable, but the social wrapper matters. The repeated “see how / see where” format appears weaker on Bluesky unless paired with a stronger insight or timely hook.

### 4. Instagram’s Strongest Sample Post Was a Broader Product/Value Post

The best visible Instagram post in the sample was:

> “Download the Goods Unite Us app and check out how the brands you buy affect our elections.”

It reached the 100th percentile within the small Instagram sample. This post works because it explains the product value in plain language. It does not require the viewer to understand a specific politician, company, or issue before caring.

Instagram pilot signal:

| Instagram content type | Posts | Avg engagements | Avg percentile |
| --- | ---: | ---: | ---: |
| Image posts | 2 | 41.0 | 80.0 |
| App download prompt | 1 | 16.0 | 90.0 |
| Politician cards | 2 | 6.0 | 60.0 |
| Company cards | 2 | 4.0 | 40.0 |
| Issue breakdowns | 4 | 3.2 | 30.0 |

Interpretation: sample size is small, but broader app-value posts and visually clear posts deserve more testing.

### 5. Threads Needs Native Metrics Before Performance Conclusions

Threads scraping recovered content but not reliable performance metrics. The language review suggests two lanes:

- Breaking donation alerts.
- App lookup prompts.

The next useful test is whether breaking donation posts generate more replies/reposts than “see how / see where” lookup prompts, but this requires Threads Insights/API data.

### 6. LLM Labels Reinforce The Creative Pattern

The local LLM classifier labeled the largest lanes as:

| LLM lane | Posts | Avg percentile | Avg engagements |
| --- | ---: | ---: | ---: |
| Politician issue card | 34 | 42.6 | 13.9 |
| Issue breakdown | 28 | 49.9 | 17.9 |
| Other/general | 25 | 51.5 | 14.8 |
| Company callout | 12 | 67.0 | 25.3 |
| Brand value | 6 | 68.4 | 21.0 |
| Community prompt | 5 | 69.8 | 22.2 |

The emotional frames with stronger average percentiles were values-based, practical, urgent, and accountability-oriented. Purely informational posts were more common but averaged lower. This supports the manual read: posts work better when they feel like a clear social statement, practical prompt, or values-framed takeaway rather than a neutral index entry.

## Manual Review Takeaways

The manual review suggests one core creative issue:

> Goods Unite Us has valuable raw material, but many posts ask for the click before giving enough value in the feed.

What works better:

- A concrete fact.
- A surprising relationship.
- A reason to care.
- One clean CTA.
- A caption that is useful even if the viewer does not click.

What seems weaker:

- Captions that only route to the app.
- Repeated “see how / see where” templates without a takeaway.
- Multiple CTAs at once: URL, app download, link in bio, hashtags.
- Hashtag-only captions unless the visual fully carries the message.

## Platform Recommendations

### Instagram

Use Instagram for visual proof, carousels, app education, and “buy this/not that” comparisons.

Recommended formats:

- Carousels explaining one company/issue relationship.
- Reels showing the app in use.
- Brand comparison graphics.
- Broad app-value posts explaining why Goods Unite Us matters.
- “Before you buy” style posts.

Creative guidance:

- Prioritize saves and shares once native metrics are available.
- Put the key takeaway in the caption, not only in the graphic.
- Reduce CTA clutter.
- Test broader brand/app education against narrow issue-card posts.

### Threads

Use Threads for conversational, values-based posts.

Recommended formats:

- Short opinionated posts.
- Questions.
- News reactions.
- Warm rewrites of strong Bluesky/X posts.
- Donation alerts with one “why this matters” sentence.

Creative guidance:

- Make posts sound less headline-like than X.
- Use more conversational phrasing.
- Test replies/reposts once Threads Insights are available.

### Bluesky

Use Bluesky for sharper commentary, political-audience discovery, and repostable data points.

Recommended formats:

- Direct fact + implication.
- Short commentary on campaign finance.
- Repostable data points.
- Image posts with a clear text takeaway.
- Company/public-figure callouts with context.

Creative guidance:

- Do not rely too heavily on app lookup templates.
- Add the social takeaway before the link.
- Judge success by repost/reply/like ratios and follower growth when impressions are unavailable.

### X/Twitter

Use X for breaking news, public figures, company callouts, and rapid-response posts.

Recommended formats:

- Donation alerts.
- Real-time political/company news reactions.
- Short threads with source/context.
- Company accountability posts.

Data need:

- Use authorized X API/export for impressions, bookmarks, link clicks, reposts, quotes, and replies.

### TikTok

Only pursue TikTok if Goods Unite Us can create native short-form video.

Recommended concepts:

- “I searched the brand before buying.”
- “3 brands that surprised us.”
- “What your grocery cart funds.”
- “Before you buy this...”
- Comment-response videos.
- Screen-recorded app walkthroughs.

Data need:

- Track views, watch time, completion rate, shares, saves, comments, and profile actions.

## Recommended Content Tests

### Test 1: Database Output vs Feed-Native Takeaway

Hypothesis: posts with a standalone takeaway will outperform lookup-style captions.

Example variants:

- Control: “See how [Company] feels about [Issue].”
- Variant: “This brand’s political footprint may surprise you. Here is the issue to check before you buy.”

### Test 2: Broad App Value vs Specific Issue Card

Hypothesis: broader product/value framing improves Instagram saves/shares and top-of-funnel engagement.

Example variants:

- “Check how brands you buy affect elections.”
- “See where [Company] stands on [Issue].”

### Test 3: Breaking Donation Alert With Context

Hypothesis: adding a “why it matters” sentence improves reposts/replies.

Example variants:

- Control: donor + amount + PAC.
- Variant: donor + amount + PAC + why the race/company connection matters.

### Test 4: CTA Simplification

Hypothesis: one clear CTA outperforms posts with URL + link in bio + app download + hashtags.

Example variants:

- Link in bio only.
- Download app only.
- Read full breakdown only.

### Test 5: Visual Format

Hypothesis: carousel/app walkthrough posts outperform static issue cards on Instagram.

Example variants:

- Static issue card.
- Carousel explaining the issue.
- Short Reel showing the app lookup.

## LLM Workflow Recommendation

Use LLMs for descriptive content intelligence, not political persuasion optimization. We now have a local Ollama-based first pass, which should be treated as a descriptive aid and reviewed against native analytics when those are available.

LLM labels should include:

- Content lane.
- Topic.
- Emotional frame.
- Audience.
- CTA type.
- Clarity score.
- Shareability score.
- Visual score.
- Failure reason.
- Repurpose recommendation.

LLM output should be joined to performance data to answer:

- Which content lanes overperform by platform?
- Which CTAs correlate with saves/shares/reposts?
- Which hooks correlate with replies/comments?
- Which visual patterns should be repeated?
- Which posts are strong candidates for repurposing?

## Data Gaps

To turn this into a true six-month analytics report, Goods Unite Us should provide at least one of:

- Meta Instagram API access.
- Threads API access.
- Native Instagram/Threads analytics exports.
- X API/export.
- TikTok analytics export/API.
- A consented analytics tool export, such as Ayrshare, Phyllo, Metricool, Sprout, Hootsuite, Buffer, or Later.

Priority metrics:

- Reach.
- Impressions/views.
- Saves.
- Shares.
- Link clicks.
- Profile visits.
- Follows from post.
- Bookmarks.
- Watch time/completion rate for video.

## 90-Day Pilot

| Timeframe | Work |
| --- | --- |
| Weeks 1-2 | Export/API pull last 6-12 months of posts and metrics |
| Weeks 3-4 | LLM labeling, visual review, normalized scoring |
| Weeks 5-6 | Identify winning/losing patterns and platform differences |
| Weeks 7-10 | Generate and publish structured test variants |
| Weeks 11-12 | Analyze results and create repeatable content playbook |

## Final Recommendation

Proceed with the current public-content analysis as the first exploratory deliverable, but clearly label it as public-visible and directional. The most important next move is not more scraping. It is joining native analytics to the content dataset, then using LLM annotations to identify repeatable content patterns.

In the meantime, the immediate creative recommendation is:

> Keep the app/database-backed content, but make each post feel like a complete social object: a fact, a reason to care, and one simple next action.
