from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


def numeric(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except Exception:
        return None


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def grouped(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get(key, "")].append(row)
    output = []
    for value, group_rows in sorted(groups.items()):
        percentiles = [numeric(row.get("platform_percentile", "")) for row in group_rows]
        percentiles = [value for value in percentiles if value is not None]
        engagements = [numeric(row.get("total_engagements", "")) for row in group_rows]
        engagements = [value for value in engagements if value is not None]
        output.append(
            {
                key: value,
                "post_count": str(len(group_rows)),
                "avg_platform_percentile": f"{mean(percentiles):.1f}" if percentiles else "",
                "avg_total_engagements": f"{mean(engagements):.1f}" if engagements else "",
                "avg_clarity": f"{mean(numeric(row.get('llm_clarity_score', '')) or 0 for row in group_rows):.1f}",
                "avg_shareability": f"{mean(numeric(row.get('llm_shareability_score', '')) or 0 for row in group_rows):.1f}",
                "avg_risk": f"{mean(numeric(row.get('llm_risk_score', '')) or 0 for row in group_rows):.1f}",
                "avg_visual": f"{mean(numeric(row.get('llm_visual_score', '')) or 0 for row in group_rows):.1f}",
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def markdown(rows: list[dict[str, str]], lane_rows: list[dict[str, str]], frame_rows: list[dict[str, str]]) -> str:
    platform_counts = Counter(row.get("platform", "") for row in rows)
    lane_counts = Counter(row.get("llm_content_lane", "") for row in rows)
    frame_counts = Counter(row.get("llm_emotional_frame", "") for row in rows)
    cta_counts = Counter(row.get("llm_cta_type", "") for row in rows)

    lines = [
        "# LLM Annotation Summary",
        "",
        "## Coverage",
        "",
        f"- Classified rows: {len(rows)}",
        f"- Platforms: {dict(platform_counts)}",
        f"- Models: {dict(Counter(row.get('llm_model', '') for row in rows))}",
        "",
        "## Label Mix",
        "",
        f"- Content lanes: {dict(lane_counts.most_common())}",
        f"- Emotional frames: {dict(frame_counts.most_common())}",
        f"- CTA types: {dict(cta_counts.most_common())}",
        "",
        "## Content Lane Performance",
        "",
        "| Content lane | Posts | Avg percentile | Avg engagements | Clarity | Shareability | Risk | Visual |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in lane_rows:
        lines.append(
            f"| {row.get('llm_content_lane', '')} | {row.get('post_count', '')} | "
            f"{row.get('avg_platform_percentile', '')} | {row.get('avg_total_engagements', '')} | "
            f"{row.get('avg_clarity', '')} | {row.get('avg_shareability', '')} | "
            f"{row.get('avg_risk', '')} | {row.get('avg_visual', '')} |"
        )

    lines.extend(
        [
            "",
            "## Emotional Frame Performance",
            "",
            "| Emotional frame | Posts | Avg percentile | Avg engagements | Clarity | Shareability | Risk | Visual |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in frame_rows:
        lines.append(
            f"| {row.get('llm_emotional_frame', '')} | {row.get('post_count', '')} | "
            f"{row.get('avg_platform_percentile', '')} | {row.get('avg_total_engagements', '')} | "
            f"{row.get('avg_clarity', '')} | {row.get('avg_shareability', '')} | "
            f"{row.get('avg_risk', '')} | {row.get('avg_visual', '')} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- These are local Ollama annotations, not OpenAI API annotations.",
            "- Use the labels as a descriptive aid, then validate against native analytics when available.",
            "- The model labels should not be used to optimize political persuasion. They are intended to describe format, clarity, CTA structure and repurposing opportunities.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize LLM-classified social post outputs.")
    parser.add_argument("--input", type=Path, default=Path("decodo_travel_scraper/outputs/llm/social_posts_llm_classified.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/llm"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input)
    lane_rows = grouped(rows, "llm_content_lane")
    frame_rows = grouped(rows, "llm_emotional_frame")
    fields = [
        "llm_content_lane",
        "llm_emotional_frame",
        "post_count",
        "avg_platform_percentile",
        "avg_total_engagements",
        "avg_clarity",
        "avg_shareability",
        "avg_risk",
        "avg_visual",
    ]
    write_csv(args.output_dir / "llm_content_lane_summary.csv", lane_rows, fields)
    write_csv(args.output_dir / "llm_emotional_frame_summary.csv", frame_rows, fields)
    (args.output_dir / "llm_annotation_summary.md").write_text(markdown(rows, lane_rows, frame_rows), encoding="utf-8")
    print(f"Wrote LLM summaries to {args.output_dir}")


if __name__ == "__main__":
    main()
