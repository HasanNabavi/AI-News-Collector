import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

INPUT_FILE = PROJECT_DIR / "F1_NewsAfterAIGroupingRun.json"
OUTPUT_FILE = SCRIPT_DIR / "Test_AIforContentGeneration.json"

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL = "qwen/qwen3.8-27b:free"

ARTICLES_PER_TEST = 1
REQUEST_TIMEOUT_SECONDS = 180
MAX_TOKENS = 1400
TEMPERATURE = 0.2
SAVE_ORIGINAL_TEXT = True


# ============================================================
# General helpers
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(data):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = OUTPUT_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temporary_file.replace(OUTPUT_FILE)


def get_article_text(article):
    scraped_data = article.get("scraped_data", {})

    if not isinstance(scraped_data, dict):
        return ""

    return scraped_data.get("text", "") or ""


def extract_json(text):
    text = (text or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        value = json.loads(text)

        if isinstance(value, dict):
            return value

    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        value = json.loads(text[start:end + 1])

        if isinstance(value, dict):
            return value

    raise ValueError("The model did not return a valid JSON object.")


def validate_news_output(value):
    if not isinstance(value, dict):
        raise ValueError("Output must be a JSON object.")

    headline = value.get("headline")
    short_text = value.get("short_text")
    key_points = value.get("key_points")

    if not isinstance(headline, str) or not headline.strip():
        raise ValueError("Missing or invalid headline.")

    if not isinstance(short_text, str) or not short_text.strip():
        raise ValueError("Missing or invalid short_text.")

    if not isinstance(key_points, list) or not key_points:
        raise ValueError("key_points must be a non-empty list.")

    if not all(
        isinstance(point, str) and point.strip()
        for point in key_points
    ):
        raise ValueError("Every key point must be a non-empty string.")

    return {
        "headline": headline.strip(),
        "short_text": short_text.strip(),
        "key_points": [point.strip() for point in key_points],
    }


def sum_tokens(stages):
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    totals = {}

    for key in keys:
        values = [
            stage.get(key)
            for stage in stages
            if stage.get(key) is not None
        ]

        totals[key] = sum(values) if values else None

    return totals


# ============================================================
# OpenRouter API
# ============================================================

def call_model(prompt, stage_name):
    if not API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Add it as a GitHub Actions "
            "repository secret named OPENROUTER_API_KEY."
        )

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }

    request_data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=request_data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": (
                "https://github.com/HasanNabavi/AI-News-Collector"
            ),
            "X-Title": "AI News Collector Content Generation Test",
        },
        method="POST",
    )

    started = time.monotonic()

    print(
        f"[REQUEST START] stage={stage_name} "
        f"model={MODEL} time={utc_now()}",
        flush=True,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            body = response.read().decode("utf-8")

        data = json.loads(body)

    except urllib.error.HTTPError as error:
        details = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"OpenRouter HTTP {error.code} during {stage_name}: "
            f"{details[:3000]}"
        ) from error

    except Exception as error:
        raise RuntimeError(
            f"OpenRouter request failed during {stage_name}: "
            f"{type(error).__name__}: {error}"
        ) from error

    elapsed = round(time.monotonic() - started, 3)
    choices = data.get("choices") or []

    if not choices:
        raise RuntimeError(
            f"OpenRouter returned no choices during {stage_name}: "
            f"{json.dumps(data, ensure_ascii=False)[:2000]}"
        )

    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict)
            else str(part)
            for part in content
        )

    usage = data.get("usage") or {}

    result = {
        "stage": stage_name,
        "status": "success" if content.strip() else "empty_response",
        "elapsed_seconds": elapsed,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "finish_reason": choice.get("finish_reason"),
        "raw_output": content,
    }

    print(
        f"[REQUEST END] stage={stage_name} "
        f"elapsed={elapsed}s "
        f"prompt_tokens={result['prompt_tokens']} "
        f"completion_tokens={result['completion_tokens']}",
        flush=True,
    )

    if not content.strip():
        raise RuntimeError(
            f"OpenRouter returned empty content during {stage_name}."
        )

    return result


# ============================================================
# Prompt construction
# ============================================================

OUTPUT_SCHEMA = """Return only one JSON object in this exact structure:
{
  "headline": "A concise Persian headline",
  "short_text": "A short Persian news item of 2 to 4 sentences",
  "key_points": [
    "A distinct factual point",
    "Another distinct factual point",
    "A third distinct factual point"
  ]
}"""


def article_context(article):
    return (
        f"Source: {article.get('source', '')}\n"
        f"Category: {article.get('category', '')}\n"
        f"Original headline (metadata only): "
        f"{article.get('title', '')}\n\n"
        f"ARTICLE TEXT:\n{get_article_text(article)}"
    )


def prompt_direct(article):
    return f"""You are a careful Persian-language news editor.

Write a short, accurate Persian news item using only facts supported
by the article. Do not invent or infer names, numbers, dates, quotes,
causes, or conclusions. Preserve uncertainty and nuance.
Use natural, clear Persian for a general audience.

The short_text should usually have 2 to 4 concise sentences.
Provide 3 to 5 distinct factual key points.
Do not repeat the short_text in the key points.
Do not add commentary or a source list.
All output fields must be in Persian.

{OUTPUT_SCHEMA}

{article_context(article)}"""


def prompt_english_draft(article):
    return f"""You are a careful English-language news editor.

Create a concise English news item from the article below.
Use only explicit facts; do not invent details, exaggerate, or add
commentary. Preserve uncertainty and nuance.

Return only valid JSON with this structure:
{{
  "headline": "A concise English headline",
  "short_text": "A short English news item of 2 to 4 sentences",
  "key_points": [
    "A distinct factual point",
    "Another factual point",
    "A third factual point"
  ]
}}

{article_context(article)}"""


def prompt_translate(english_json):
    return f"""Translate and adapt the following English news item into
natural, fluent Persian.

This is translation, not a new reporting task.
Preserve every factual detail and uncertainty.
Do not add, remove, strengthen, or infer claims.
Keep the headline concise, the short_text to 2–4 short sentences,
and the key points distinct.
All output fields must be in Persian.

Return only one valid JSON object in this exact structure:
{OUTPUT_SCHEMA}

ENGLISH NEWS ITEM:
{json.dumps(english_json, ensure_ascii=False, indent=2)}"""


def prompt_extract_facts(article):
    return f"""Extract the key verifiable facts from the article below
for a news editor.

Do not write a news story yet. Do not infer anything.
Preserve exact names, quantities, dates, attribution, and uncertainty.
If a detail is not stated, omit it.

Return only valid JSON with these keys:
{{
  "event": "What happened, in one factual sentence",
  "people_and_organizations": [
    "Names and their roles if stated"
  ],
  "numbers_and_dates": [
    "Exact numbers, units, and dates stated"
  ],
  "other_verified_facts": [
    "One fact per item"
  ],
  "uncertainties_or_attributions": [
    "Claims attributed to a source or stated uncertainly"
  ]
}}

{article_context(article)}"""


def prompt_from_facts(article, facts):
    return f"""You are a careful Persian-language news editor.

Write a concise, natural Persian news item using ONLY the extracted
facts below. Do not use outside knowledge or add claims not present
in the facts. Keep names, numbers, units, attribution, and uncertainty
accurate.

The short_text should contain 2 to 4 short sentences.
Provide 3 to 5 distinct key points.
All output fields must be in Persian.

Return only one valid JSON object in this exact structure:
{OUTPUT_SCHEMA}

ARTICLE METADATA:
Source: {article.get('source', '')}
Category: {article.get('category', '')}
Original headline (metadata only): {article.get('title', '')}

EXTRACTED FACTS:
{json.dumps(facts, ensure_ascii=False, indent=2)}"""


# ============================================================
# Test methods
# ============================================================

def run_one_stage_method(
    article,
    method_id,
    method_name,
    prompt,
):
    method = {
        "method_id": method_id,
        "method_name": method_name,
        "status": "error",
        "request_count": 1,
        "stages": [],
        "output": None,
        "error": None,
    }

    try:
        response = call_model(prompt, f"{method_id}_generation")
        method["stages"].append(response)

        parsed = extract_json(response["raw_output"])
        method["output"] = validate_news_output(parsed)
        method["status"] = "success"

    except Exception as error:
        method["error"] = f"{type(error).__name__}: {error}"

    method["elapsed_seconds"] = round(
        sum(stage.get("elapsed_seconds", 0)
            for stage in method["stages"]),
        3,
    )

    method["token_totals"] = sum_tokens(method["stages"])
    return method


def run_two_stage_method(
    article,
    method_id,
    method_name,
    first_prompt,
    second_prompt_builder,
):
    method = {
        "method_id": method_id,
        "method_name": method_name,
        "status": "error",
        "request_count": 0,
        "stages": [],
        "intermediate_output": None,
        "output": None,
        "error": None,
    }

    try:
        first = call_model(first_prompt, f"{method_id}_stage_1")
        method["stages"].append(first)
        method["request_count"] += 1

        intermediate = extract_json(first["raw_output"])
        method["intermediate_output"] = intermediate

        second = call_model(
            second_prompt_builder(intermediate),
            f"{method_id}_stage_2",
        )

        method["stages"].append(second)
        method["request_count"] += 1

        parsed = extract_json(second["raw_output"])
        method["output"] = validate_news_output(parsed)
        method["status"] = "success"

    except Exception as error:
        method["error"] = f"{type(error).__name__}: {error}"

    method["elapsed_seconds"] = round(
        sum(stage.get("elapsed_seconds", 0)
            for stage in method["stages"]),
        3,
    )

    method["token_totals"] = sum_tokens(method["stages"])
    return method


# ============================================================
# Main
# ============================================================

def main():
    started_at = utc_now()
    run_started = time.monotonic()

    print("=" * 64, flush=True)
    print("OPENROUTER: THREE CONTENT-GENERATION METHODS", flush=True)
    print(f"Model: {MODEL}", flush=True)
    print("=" * 64, flush=True)

    if not API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured. Add it in GitHub "
            "repository Settings > Secrets and variables > Actions."
        )

    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        input_data = json.load(file)

    articles = input_data.get("news", [])

    if not isinstance(articles, list) or not articles:
        raise ValueError(
            "Input JSON must contain a non-empty 'news' list."
        )

    articles = articles[:ARTICLES_PER_TEST]
    article = articles[0]
    original_text = get_article_text(article)

    if not original_text.strip():
        raise ValueError("The selected article has no scraped text.")

    print(f"Input: {INPUT_FILE}", flush=True)
    print(f"Selected articles: {len(articles)}", flush=True)
    print(
        f"Original text length: {len(original_text)} characters",
        flush=True,
    )

    results = {
        "test_metadata": {
            "test_name": "Test_AIforContentGeneration",
            "purpose": (
                "Compare three Persian news-generation workflows "
                "on the same article."
            ),
            "provider": "OpenRouter",
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tokens_per_request": MAX_TOKENS,
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "started_at": started_at,
            "finished_at": None,
            "elapsed_seconds": None,
        },
        "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
        "output_file": str(OUTPUT_FILE.relative_to(PROJECT_DIR)),
        "article_count": len(articles),
        "articles": [
            {
                "article_index": 0,
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "category": article.get("category", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at"),
                "group_id": article.get("group_id"),
                "original_text_characters": len(original_text),
                **(
                    {"original_text": original_text}
                    if SAVE_ORIGINAL_TEXT else {}
                ),
            }
        ],
        "method_results": {},
    }

    save_json(results)

    methods = [
        (
            "method_1_direct_persian",
            "Direct Persian generation from the original English article",
            lambda: run_one_stage_method(
                article,
                "method_1_direct_persian",
                "Direct Persian generation",
                prompt_direct(article),
            ),
        ),
        (
            "method_2_english_then_persian",
            "Generate English news first, then translate it into Persian",
            lambda: run_two_stage_method(
                article,
                "method_2_english_then_persian",
                "English draft followed by Persian translation",
                prompt_english_draft(article),
                prompt_translate,
            ),
        ),
        (
            "method_3_facts_then_persian",
            "Extract explicit facts first, then write Persian from them",
            lambda: run_two_stage_method(
                article,
                "method_3_facts_then_persian",
                "Fact extraction followed by Persian generation",
                prompt_extract_facts(article),
                lambda facts: prompt_from_facts(article, facts),
            ),
        ),
    ]

    for method_key, method_description, runner in methods:
        print(f"\n[METHOD START] {method_key}", flush=True)
        method_started = time.monotonic()

        method_result = runner()
        method_result["description"] = method_description
        method_result["wall_clock_elapsed_seconds"] = round(
            time.monotonic() - method_started,
            3,
        )

        results["method_results"][method_key] = method_result
        save_json(results)

        print(
            f"[METHOD END] {method_key} "
            f"status={method_result['status']} "
            f"elapsed={method_result['wall_clock_elapsed_seconds']}s",
            flush=True,
        )

    results["test_metadata"]["finished_at"] = utc_now()
    results["test_metadata"]["elapsed_seconds"] = round(
        time.monotonic() - run_started,
        3,
    )

    results["test_metadata"]["total_api_requests"] = sum(
        item.get("request_count", 0)
        for item in results["method_results"].values()
    )

    results["test_metadata"]["successful_methods"] = sum(
        item.get("status") == "success"
        for item in results["method_results"].values()
    )

    save_json(results)

    print("\n" + "=" * 64, flush=True)
    print(f"Test complete. Output: {OUTPUT_FILE}", flush=True)
    print(
        "Successful methods: "
        f"{results['test_metadata']['successful_methods']}/3",
        flush=True,
    )
    print(
        "API requests: "
        f"{results['test_metadata']['total_api_requests']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
