# Social Content Analysis

## Dataset status

- Total rows: 113
- Platform counts: {'bluesky': 97, 'instagram': 12, 'threads': 4}
- Data quality counts: {('bluesky', 'complete'): 97, ('instagram', 'complete'): 11, ('instagram', 'out_of_scope'): 1, ('threads', 'content_only'): 4}

## First-pass findings

- Bluesky is the strongest analysis base right now because it has the most complete public post and engagement data.
- Instagram now has usable public post data for owned Goods Unite Us posts, but still lacks private metrics such as reach, saves and shares.
- Threads has text/content only from scraping; meaningful performance analysis should wait for Threads Insights/API export.
- Percentiles are platform-relative, which avoids treating small-network and larger-network raw engagement as directly equivalent.

## Content mix among complete rows

- Topics: {'general_brand': 49, 'company_issue_position': 17, 'politician_issue_position': 17, 'app_promotion': 15, 'political_donations': 4, 'issue_position': 4, 'consumer_action': 2}
- Content types: {'image_post': 40, 'text_post': 29, 'company_card': 15, 'politician_card': 15, 'breaking_donation_alert': 4, 'issue_breakdown': 4, 'app_download_prompt': 1}

## Top posts by platform-relative percentile

### Bluesky
- 100.0 percentile, 118 engagements, image_post: #USPOL
- 99.0 percentile, 97 engagements, image_post: Did you know that Ashley Furniture is a big donor to Donald Trump and Senator Ron Johnson? Now you know. Shop with purpose.
- 97.9 percentile, 91 engagements, text_post: #goodsuniteus #campaignfinancereform #politics
- 96.9 percentile, 77 engagements, text_post: Let us introduce you to Index Align! #politics
- 95.8 percentile, 75 engagements, text_post: #USPOL Goods Unite Us

### Instagram
- 100.0 percentile, 76 engagements, image_post: Download the Goods Unite Us app and check out how the brands you buy affect our elections. #politics #boycott #money
- 90.0 percentile, 16 engagements, app_download_prompt: Vote with your wallet. Download the Goods app. #politics #vote #boycott
- 80.0 percentile, 8 engagements, issue_breakdown: See how Progressive feels about LGBTQ Rights. Full breakdown: https://www.goodsuniteus.com/issues/-LX7m60\_y5uDkDSt5eaK (link in bio) #GoodsUniteUs #VoteWithYourWallet #Corporat...
- 70.0 percentile, 7 engagements, politician_card: See where Jon Ossoff stands on Abortion & Reproductive Rights. Download the free app to see more → link in bio (https://www.goodsuniteus.com/politician/-LaTXI9KG9AvhyNOFzGZ) #Go...
- 60.0 percentile, 6 engagements, image_post: #politics #boycott #vote

## Recommendations

1. Treat this as a public-content pilot, not the final six-month analytics dataset.
2. Get Meta/Threads owned-account exports or API access for reach, saves, shares and views.
3. Use the enriched CSV to run LLM review on post language once owned metrics are joined.
4. Keep Bluesky API collection as the reliable baseline and schedule it for regular refreshes.
5. Use Instagram scraping only as a fallback for public captions, dates and visible engagement.

## Analysis table

| Platform | Group | Posts | Avg engagements | Avg percentile | Top quartile posts |
| --- | --- | ---: | ---: | ---: | ---: |
| bluesky | breaking_donation_alert | 4 | 2.5 | 28.4 | 0 |
| bluesky | company_card | 13 | 2.2 | 28.3 | 0 |
| bluesky | image_post | 38 | 26.0 | 62.3 | 14 |
| bluesky | politician_card | 13 | 1.1 | 20.3 | 0 |
| bluesky | text_post | 29 | 23.7 | 67.8 | 11 |
| instagram | app_download_prompt | 1 | 16.0 | 90.0 | 1 |
| instagram | company_card | 2 | 4.0 | 40.0 | 0 |
| instagram | image_post | 2 | 41.0 | 80.0 | 1 |
| instagram | issue_breakdown | 4 | 3.2 | 30.0 | 1 |
| instagram | politician_card | 2 | 6.0 | 60.0 | 0 |
