# LLM Annotation Summary

## Coverage

- Classified rows: 112
- Platforms: {'bluesky': 97, 'instagram': 11, 'threads': 4}
- Models: {'ollama:llama3.1:8b': 112}

## Label Mix

- Content lanes: {'politician_issue_card': 34, 'issue_breakdown': 28, 'other': 25, 'company_callout': 12, 'brand_value': 6, 'community_prompt': 5, 'app_education': 1, 'news_reaction': 1}
- Emotional frames: {'informational': 40, 'neutral': 25, 'accountability': 22, 'practical': 11, 'values_based': 7, 'surprising': 4, 'urgent': 3}
- CTA types: {'link_in_bio': 50, 'none': 49, 'download_app': 9, 'other': 2, 'vote_with_wallet': 1, 'learn_more': 1}

## Content Lane Performance

| Content lane | Posts | Avg percentile | Avg engagements | Clarity | Shareability | Risk | Visual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| app_education | 1 | 78.1 | 24.0 | 5.0 | 4.0 | 1.0 | 5.0 |
| brand_value | 6 | 68.4 | 21.0 | 4.5 | 3.7 | 2.2 | 5.0 |
| community_prompt | 5 | 69.8 | 22.2 | 3.8 | 4.0 | 1.6 | 5.0 |
| company_callout | 12 | 67.0 | 25.3 | 4.2 | 3.2 | 2.7 | 4.2 |
| issue_breakdown | 28 | 49.9 | 17.9 | 4.3 | 3.0 | 3.2 | 2.6 |
| news_reaction | 1 | 70.8 | 16.0 | 5.0 | 3.0 | 1.0 | 1.0 |
| other | 25 | 51.5 | 14.8 | 3.2 | 2.8 | 1.9 | 4.2 |
| politician_issue_card | 34 | 42.6 | 13.9 | 4.8 | 3.3 | 3.5 | 2.8 |

## Emotional Frame Performance

| Emotional frame | Posts | Avg percentile | Avg engagements | Clarity | Shareability | Risk | Visual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| accountability | 22 | 57.4 | 21.4 | 4.3 | 3.4 | 3.8 | 3.5 |
| informational | 40 | 38.9 | 11.4 | 4.7 | 3.0 | 3.1 | 2.1 |
| neutral | 25 | 57.2 | 18.3 | 3.2 | 2.8 | 1.8 | 4.3 |
| practical | 11 | 65.2 | 25.7 | 4.5 | 3.3 | 2.1 | 5.0 |
| surprising | 4 | 38.2 | 4.5 | 3.5 | 3.0 | 2.5 | 4.2 |
| urgent | 3 | 64.8 | 28.0 | 4.7 | 3.7 | 3.7 | 4.0 |
| values_based | 7 | 73.0 | 20.7 | 4.6 | 3.9 | 2.3 | 4.7 |

## Interpretation Notes

- These are local Ollama annotations, not OpenAI API annotations.
- Use the labels as a descriptive aid, then validate against native analytics when available.
- The model labels should not be used to optimize political persuasion. They are intended to describe format, clarity, CTA structure and repurposing opportunities.
