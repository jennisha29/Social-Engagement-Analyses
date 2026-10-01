from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROMPT_VERSION = "social_content_descriptive_v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
RESPONSES_URL = "https://api.openai.com/v1/responses"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

ANNOTATION_FIELDS = [
    "post_id",
    "platform",
    "post_url",
    "prompt_version",
    "model",
    "classified_at",
    "content_lane",
    "topic",
    "emotional_frame",
    "audience",
    "cta_type",
    "clarity_score",
    "shareability_score",
    "risk_score",
    "visual_score",
    "summary",
    "failure_reason",
    "repurpose_recommendation",
    "confidence",
    "raw_llm_json",
]


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "content_lane": {
            "type": "string",
            "enum": [
                "app_education",
                "brand_value",
                "company_callout",
                "politician_issue_card",
                "donation_alert",
                "issue_breakdown",
                "news_reaction",
                "consumer_action",
                "community_prompt",
                "other",
            ],
        },
        "topic": {"type": "string"},
        "emotional_frame": {
            "type": "string",
            "enum": ["informational", "urgent", "surprising", "accountability", "values_based", "practical", "neutral"],
        },
        "audience": {
            "type": "string",
            "enum": ["general_consumers", "politically_engaged", "journalists_researchers", "app_users", "supporters", "unclear"],
        },
        "cta_type": {
            "type": "string",
            "enum": ["download_app", "link_in_bio", "learn_more", "read_breakdown", "share_discuss", "vote_with_wallet", "none", "other"],
        },
        "clarity_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "shareability_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "risk_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "visual_score": {"type": "integer", "minimum": 1, "maximum": 5},
        "summary": {"type": "string"},
        "failure_reason": {"type": "string"},
        "repurpose_recommendation": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "content_lane",
        "topic",
        "emotional_frame",
        "audience",
        "cta_type",
        "clarity_score",
        "shareability_score",
        "risk_score",
        "visual_score",
        "summary",
        "failure_reason",
        "repurpose_recommendation",
        "confidence",
    ],
}


SYSTEM_PROMPT = """You classify social media posts for a descriptive content audit.

Important boundaries:
- Keep the analysis descriptive and platform/content focused.
- Do not recommend targeted political persuasion tactics.
- Do not infer sensitive personal traits about audiences.
- Scores should describe clarity, shareability, visual usefulness, and ambiguity/risk based on the post content only.
- Risk score means brand/clarity/reputational ambiguity risk, not civic or electoral persuasion risk.
- If a field is uncertain, choose the closest label and lower confidence.
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def score_from_percentile(value: str) -> int:
    try:
        pct = float(value)
    except Exception:
        return 3
    if pct >= 80:
        return 5
    if pct >= 60:
        return 4
    if pct >= 40:
        return 3
    if pct >= 20:
        return 2
    return 1


def heuristic_annotation(row: dict[str, str]) -> dict[str, Any]:
    text = row.get("post_text", "")
    lower = text.lower()
    if lower.startswith("breaking:") or "gave $" in lower:
        lane = "donation_alert"
        frame = "urgent"
    elif "vote with your wallet" in lower:
        lane = "consumer_action"
        frame = "values_based"
    elif "see where" in lower and "stands on" in lower:
        lane = "politician_issue_card"
        frame = "informational"
    elif "see how" in lower and "feels about" in lower:
        lane = "company_callout"
        frame = "informational"
    elif "download" in lower or "app" in lower:
        lane = "app_education"
        frame = "practical"
    elif "full breakdown" in lower:
        lane = "issue_breakdown"
        frame = "informational"
    else:
        lane = "brand_value" if row.get("platform") == "instagram" else "other"
        frame = "neutral"

    if "download" in lower:
        cta = "download_app"
    elif "link in bio" in lower:
        cta = "link_in_bio"
    elif "full breakdown" in lower:
        cta = "read_breakdown"
    elif "vote with your wallet" in lower:
        cta = "vote_with_wallet"
    elif "http" in lower:
        cta = "learn_more"
    else:
        cta = "none"

    clarity = 4 if len(text) > 20 else 2
    if len(text) > 220:
        clarity -= 1
    visual_score = 4 if row.get("image_url") else 2
    shareability = score_from_percentile(row.get("platform_percentile", ""))
    risk = 3 if any(term in lower for term in ["israel", "dei", "abortion", "gun control"]) else 2

    return {
        "content_lane": lane,
        "topic": "unknown" if not text else compact(text[:80]),
        "emotional_frame": frame,
        "audience": "politically_engaged" if lane in {"donation_alert", "company_callout", "politician_issue_card"} else "general_consumers",
        "cta_type": cta,
        "clarity_score": max(1, min(5, clarity)),
        "shareability_score": shareability,
        "risk_score": risk,
        "visual_score": visual_score,
        "summary": compact(text[:180]) or "No post text available.",
        "failure_reason": "May feel like a lookup result rather than a complete feed-native post." if lane in {"company_callout", "politician_issue_card"} else "No obvious failure reason from text-only review.",
        "repurpose_recommendation": "Add one concrete takeaway before the CTA and test on the strongest matching platform.",
        "confidence": 0.45,
    }


def response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    pieces: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text", "")
                if text:
                    pieces.append(text)
    return "\n".join(pieces)


def classify_with_openai(row: dict[str, str], *, api_key: str, model: str, max_retries: int = 3) -> dict[str, Any]:
    user_payload = {
        "platform": row.get("platform", ""),
        "post_url": row.get("post_url", ""),
        "published_at": row.get("published_at", ""),
        "caption_text": row.get("post_text", ""),
        "media_type": row.get("media_type", ""),
        "has_image": bool(row.get("image_url")),
        "visible_metrics": {
            "likes": row.get("likes", ""),
            "comments": row.get("comments", ""),
            "replies": row.get("replies", ""),
            "shares": row.get("shares", ""),
            "reposts": row.get("reposts", ""),
            "quotes": row.get("quotes", ""),
            "total_engagements": row.get("total_engagements", ""),
            "platform_percentile": row.get("platform_percentile", ""),
        },
    }
    request_payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Classify this post as JSON using the schema. Post:\n"
                        + json.dumps(user_payload, ensure_ascii=False),
                    }
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "social_post_annotation",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }

    data = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        RESPONSES_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            text = response_text(payload)
            parsed = json.loads(text)
            parsed["_raw_response_text"] = text
            return parsed
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if attempt == max_retries or error.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"OpenAI HTTP {error.code}: {detail}") from error
            time.sleep(2 * attempt)
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("OpenAI classification failed after retries.")


def post_payload_for_prompt(row: dict[str, str]) -> dict[str, Any]:
    return {
        "platform": row.get("platform", ""),
        "post_url": row.get("post_url", ""),
        "published_at": row.get("published_at", ""),
        "caption_text": row.get("post_text", ""),
        "media_type": row.get("media_type", ""),
        "has_image": bool(row.get("image_url")),
        "visible_metrics": {
            "likes": row.get("likes", ""),
            "comments": row.get("comments", ""),
            "replies": row.get("replies", ""),
            "shares": row.get("shares", ""),
            "reposts": row.get("reposts", ""),
            "quotes": row.get("quotes", ""),
            "total_engagements": row.get("total_engagements", ""),
            "platform_percentile": row.get("platform_percentile", ""),
        },
    }


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError(f"No JSON object found in model response: {text[:300]}")
    return json.loads(match.group(0))


def sanitize_annotation(value: dict[str, Any]) -> dict[str, Any]:
    fallback = heuristic_annotation({"post_text": "", "platform": "", "platform_percentile": ""})
    merged = {**fallback, **value}

    enum_fields = {
        "content_lane": (set(SCHEMA["properties"]["content_lane"]["enum"]), "other"),
        "emotional_frame": (set(SCHEMA["properties"]["emotional_frame"]["enum"]), "neutral"),
        "audience": (set(SCHEMA["properties"]["audience"]["enum"]), "unclear"),
        "cta_type": (set(SCHEMA["properties"]["cta_type"]["enum"]), "other"),
    }
    for field, (allowed, default) in enum_fields.items():
        if merged.get(field) not in allowed:
            merged[field] = default

    for field in ["clarity_score", "shareability_score", "risk_score", "visual_score"]:
        try:
            score = int(float(merged.get(field, 3)))
        except Exception:
            score = 3
        merged[field] = max(1, min(5, score))

    try:
        confidence = float(merged.get("confidence", 0.5))
    except Exception:
        confidence = 0.5
    merged["confidence"] = max(0, min(1, confidence))

    for field in ["topic", "summary", "failure_reason", "repurpose_recommendation"]:
        merged[field] = str(merged.get(field, ""))
    return {field: merged[field] for field in SCHEMA["required"]}


def classify_with_ollama(
    row: dict[str, str],
    *,
    model: str,
    url: str,
    max_retries: int = 2,
) -> dict[str, Any]:
    instructions = (
        SYSTEM_PROMPT
        + "\nReturn only a JSON object with exactly these keys: "
        + ", ".join(SCHEMA["required"])
        + ".\nAllowed labels:\n"
        + json.dumps(
            {
                "content_lane": SCHEMA["properties"]["content_lane"]["enum"],
                "emotional_frame": SCHEMA["properties"]["emotional_frame"]["enum"],
                "audience": SCHEMA["properties"]["audience"]["enum"],
                "cta_type": SCHEMA["properties"]["cta_type"]["enum"],
            },
            ensure_ascii=False,
        )
        + "\nScores are integers 1-5. confidence is 0-1."
    )
    request_payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": "Classify this post:\n" + json.dumps(post_payload_for_prompt(row), ensure_ascii=False),
            },
        ],
        "options": {"temperature": 0.1},
    }
    data = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload.get("message", {}).get("content", "")
            parsed = sanitize_annotation(extract_json_object(content))
            parsed["_raw_response_text"] = content
            return parsed
        except urllib.error.URLError as error:
            if attempt == max_retries:
                raise RuntimeError(
                    "Could not reach Ollama. Make sure it is installed, running with `ollama serve`, "
                    f"and the model is pulled. Error: {error}"
                ) from error
            time.sleep(2 * attempt)
        except Exception:
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("Ollama classification failed after retries.")


def annotation_row(
    source: dict[str, str],
    annotation: dict[str, Any],
    *,
    model: str,
    raw_llm_json: str,
) -> dict[str, str]:
    return {
        "post_id": source.get("post_id", ""),
        "platform": source.get("platform", ""),
        "post_url": source.get("post_url", ""),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "classified_at": utc_now(),
        "content_lane": str(annotation.get("content_lane", "")),
        "topic": str(annotation.get("topic", "")),
        "emotional_frame": str(annotation.get("emotional_frame", "")),
        "audience": str(annotation.get("audience", "")),
        "cta_type": str(annotation.get("cta_type", "")),
        "clarity_score": str(annotation.get("clarity_score", "")),
        "shareability_score": str(annotation.get("shareability_score", "")),
        "risk_score": str(annotation.get("risk_score", "")),
        "visual_score": str(annotation.get("visual_score", "")),
        "summary": str(annotation.get("summary", "")),
        "failure_reason": str(annotation.get("failure_reason", "")),
        "repurpose_recommendation": str(annotation.get("repurpose_recommendation", "")),
        "confidence": str(annotation.get("confidence", "")),
        "raw_llm_json": raw_llm_json,
    }


def should_classify(row: dict[str, str], include_content_only: bool) -> bool:
    if row.get("data_quality") == "complete":
        return True
    if include_content_only and row.get("data_quality") == "content_only":
        return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify social posts with an LLM and write annotation tables.")
    parser.add_argument("--input", type=Path, default=Path("decodo_travel_scraper/outputs/social_posts_master.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("decodo_travel_scraper/outputs/llm"))
    parser.add_argument("--env-file", type=Path, default=Path("decodo_travel_scraper/.env"))
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--provider", choices=["openai", "ollama"], default="openai")
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", OLLAMA_CHAT_URL))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic placeholder annotations without API calls.")
    parser.add_argument("--include-content-only", action="store_true", help="Also classify content-only rows, such as scraped Threads rows.")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env(args.env_file)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not args.dry_run and args.provider == "openai" and not api_key:
        raise SystemExit("Set OPENAI_API_KEY in the environment or decodo_travel_scraper/.env, or run with --dry-run.")

    source_rows = [row for row in read_rows(args.input) if should_classify(row, args.include_content_only)]
    if args.limit:
        source_rows = source_rows[: args.limit]

    annotations: list[dict[str, str]] = []
    joined: list[dict[str, str]] = []
    for index, row in enumerate(source_rows, start=1):
        if args.dry_run:
            parsed = heuristic_annotation(row)
            raw_json = json.dumps(parsed, ensure_ascii=False)
            model = "dry_run_heuristic"
        elif args.provider == "ollama":
            parsed = classify_with_ollama(row, model=args.ollama_model, url=args.ollama_url)
            raw_json = parsed.pop("_raw_response_text", json.dumps(parsed, ensure_ascii=False))
            model = f"ollama:{args.ollama_model}"
            time.sleep(args.sleep_seconds)
        else:
            parsed = classify_with_openai(row, api_key=api_key, model=args.model)
            raw_json = parsed.pop("_raw_response_text", json.dumps(parsed, ensure_ascii=False))
            model = args.model
            time.sleep(args.sleep_seconds)
        ann = annotation_row(row, parsed, model=model, raw_llm_json=raw_json)
        annotations.append(ann)
        joined.append({**row, **{f"llm_{key}": value for key, value in ann.items() if key not in {"post_id", "platform", "post_url"}}})
        print(f"Classified {index}/{len(source_rows)} {row.get('platform')} {row.get('post_id')}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    annotations_path = args.output_dir / "llm_annotations.csv"
    joined_path = args.output_dir / "social_posts_llm_classified.csv"
    write_csv(annotations_path, annotations, ANNOTATION_FIELDS)
    write_csv(joined_path, joined, list(joined[0].keys()) if joined else [])
    print(f"Wrote annotations to {annotations_path}")
    print(f"Wrote joined classified posts to {joined_path}")


if __name__ == "__main__":
    main()
