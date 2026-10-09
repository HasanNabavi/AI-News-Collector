
import json
import time
import urllib.request
import urllib.error
import subprocess
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

INPUT_FILE = PROJECT_DIR / "F1_NewsAfterAIGroupingRun.json"
OUTPUT_FILE = SCRIPT_DIR / "Test_AIforContentGeneration.json"

OLLAMA_URL = "http://127.0.0.1:11434"
MODELS = [
    "qwen3:4b",
    "gemma3:4b",
]

REQUEST_TIMEOUT_SECONDS = 1800
MODEL_PULL_TIMEOUT_SECONDS = 1800

# Keep the original article text in the output for comparison.
SAVE_ORIGINAL_TEXT = True


# ============================================================
# General helpers
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(data):
    """Save the current results, including partial results."""
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
    """
    Extract a JSON object from the model response.
    Also handles responses surrounded by Markdown code fences.
    """
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

        if text.lower().startswith("json"):
            text = text[4:].strip()

    # First try parsing the entire response.
    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # If extra text surrounds the JSON, try the outermost object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:
        result = json.loads(text[start:end + 1])

        if isinstance(result, dict):
            return result

    raise ValueError("The model did not return a valid JSON object.")


# ============================================================
# Ollama connection
# ============================================================

def ollama_is_running():
    try:
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/tags",
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            return response.status == 200

    except Exception:
        return False


def start_ollama_if_needed():
    """Start the Ollama server if it is not already running."""

    if ollama_is_running():
        print("Ollama server is already running.")
        return None

    ollama_executable = shutil.which("ollama")

    if not ollama_executable:
        raise RuntimeError(
            "Ollama executable was not found. "
            "Install Ollama and make sure it is available in PATH."
        )

    print("Starting Ollama server...")

    process = subprocess.Popen(
        [ollama_executable, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        if ollama_is_running():
            print("Ollama server is ready.")
            return process

        if process.poll() is not None:
            raise RuntimeError(
                "Ollama server stopped unexpectedly."
            )

        time.sleep(2)

    raise RuntimeError(
        "Ollama server did not become ready within 60 seconds."
    )


def ensure_model_available(model_name):
    """Download a model if necessary."""

    print(f"\nChecking model: {model_name}")

    executable = shutil.which("ollama")

    if not executable:
        raise RuntimeError("Ollama executable was not found.")

    result = subprocess.run(
        [executable, "pull", model_name],
        capture_output=True,
        text=True,
        timeout=MODEL_PULL_TIMEOUT_SECONDS,
        check=False,
    )

    if result.returncode != 0:
        error_message = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"Failed to download model {model_name}."
        )

        raise RuntimeError(error_message)

    print(f"Model ready: {model_name}")


# ============================================================
# Content generation
# ============================================================

def build_prompt(article):
    title = article.get("title", "")
    source = article.get("source", "")
    category = article.get("category", "")
    article_text = get_article_text(article)

    return f"""
You are a careful Persian-language news editor.

Your task is to turn the original news article below into a
short, accurate, readable Persian news item.

IMPORTANT RULES:
1. Use only facts explicitly supported by the original article.
2. Do not invent names, numbers, dates, quotes, causes, or conclusions.
3. If a detail is uncertain or absent, do not guess.
4. Preserve the meaning and factual nuance of the article.
5. Write natural, clear Persian suitable for a general audience.
6. Do not translate word-for-word when that would sound unnatural.
7. The headline must be concise and informative.
8. The short_text should usually be 2 to 4 short Persian sentences.
9. Provide 3 to 5 concise key points in Persian.
10. Do not add an introduction, commentary, opinion, or source list.
11. Return ONLY one valid JSON object. No Markdown or code fences.
12. All generated content must be in Persian.

Return exactly this JSON structure:
{{
  "headline": "A concise Persian headline",
  "short_text": "A short Persian news item",
  "key_points": [
    "First key point",
    "Second key point",
    "Third key point"
  ]
}}

ARTICLE METADATA:
Source: {source}
Category: {category}
Original headline: {title}

ORIGINAL ARTICLE TEXT:
{article_text}
""".strip()


def call_ollama(model_name, prompt):
    """Call Ollama and return the model response and token statistics."""

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
        },
    }

    request_data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=request_data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        response_data = json.loads(
            response.read().decode("utf-8")
        )

    message = response_data.get("message", {})
    raw_output = message.get("content", "")

    if not raw_output.strip():
        raise ValueError("Ollama returned an empty response.")

    return {
        "raw_output": raw_output,
        "prompt_tokens": response_data.get("prompt_eval_count"),
        "output_tokens": response_data.get("eval_count"),
        "total_duration_ns": response_data.get("total_duration"),
        "load_duration_ns": response_data.get("load_duration"),
        "prompt_eval_duration_ns": response_data.get(
            "prompt_eval_duration"
        ),
        "eval_duration_ns": response_data.get("eval_duration"),
    }


def validate_generated_content(content):
    """Check the required output fields and their types."""

    if not isinstance(content, dict):
        raise ValueError("Output is not a JSON object.")

    headline = content.get("headline")
    short_text = content.get("short_text")
    key_points = content.get("key_points")

    if not isinstance(headline, str) or not headline.strip():
        raise ValueError("Missing or invalid headline.")

    if not isinstance(short_text, str) or not short_text.strip():
        raise ValueError("Missing or invalid short_text.")

    if not isinstance(key_points, list):
        raise ValueError("key_points must be a list.")

    if not all(
        isinstance(point, str) and point.strip()
        for point in key_points
    ):
        raise ValueError("One or more key_points are invalid.")

    return {
        "headline": headline.strip(),
        "short_text": short_text.strip(),
        "key_points": [
            point.strip() for point in key_points
        ],
    }


# ============================================================
# Main test
# ============================================================

def main():
    started_at = utc_now()
    run_started = time.time()

    print("=" * 60)
    print("AI CONTENT GENERATION MODEL TEST")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        input_data = json.load(file)

    articles = input_data.get("news", [])

    if not isinstance(articles, list):
        raise ValueError(
            "The input JSON must contain a 'news' list."
        )

    if not articles:
        raise ValueError("The input file contains no news articles.")

    print(f"Input file: {INPUT_FILE}")
    print(f"Articles found: {len(articles)}")
    print(f"Models: {', '.join(MODELS)}")

    # Store each article once, including its original text.
    saved_articles = []

    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            article = {}

        item = {
            "article_index": index,
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "category": article.get("category", ""),
            "url": article.get("url", ""),
            "published_at": article.get("published_at"),
            "group_id": article.get("group_id"),
            "original_text_characters": len(
                get_article_text(article)
            ),
        }

        if SAVE_ORIGINAL_TEXT:
            item["original_text"] = get_article_text(article)

        saved_articles.append(item)

    results = {
        "test_metadata": {
            "test_name": "Test_AIforContentGeneration",
            "purpose": (
                "Compare local Ollama models for Persian news "
                "content generation."
            ),
            "models": MODELS,
            "temperature": 0.2,
            "started_at": started_at,
            "finished_at": None,
            "elapsed_seconds": None,
        },
        "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
        "output_file": str(
            OUTPUT_FILE.relative_to(PROJECT_DIR)
        ),
        "article_count": len(articles),
        "articles": saved_articles,
        "model_results": {},
    }

    # Save the initial report before doing any model work.
    save_json(results)

    server_process = None

    try:
        server_process = start_ollama_if_needed()

        for model_name in MODELS:
            print("\n" + "=" * 60)
            print(f"MODEL: {model_name}")
            print("=" * 60)

            model_result = {
                "model": model_name,
                "status": "running",
                "started_at": utc_now(),
                "finished_at": None,
                "elapsed_seconds": None,
                "success_count": 0,
                "error_count": 0,
                "results": [],
            }

            results["model_results"][model_name] = model_result
            save_json(results)

            model_started = time.time()

            try:
                ensure_model_available(model_name)

            except Exception as error:
                model_result["status"] = "model_setup_failed"
                model_result["setup_error"] = str(error)
                model_result["finished_at"] = utc_now()
                model_result["elapsed_seconds"] = round(
                    time.time() - model_started, 3
                )

                # Record a failed result for every article.
                for index, article in enumerate(articles):
                    model_result["results"].append({
                        "article_index": index,
                        "status": "error",
                        "error": (
                            "Model setup failed: " + str(error)
                        ),
                    })

                model_result["error_count"] = len(articles)
                save_json(results)

                print(f"Could not prepare {model_name}: {error}")
                continue

            for index, article in enumerate(articles):
                title = article.get("title", "")
                article_text = get_article_text(article)

                print(
                    f"\n[{model_name}] "
                    f"Article {index + 1}/{len(articles)}: {title}"
                )

                article_started = time.time()

                item_result = {
                    "article_index": index,
                    "original_title": title,
                    "status": "error",
                    "elapsed_seconds": None,
                    "json_valid": False,
                    "prompt_tokens": None,
                    "output_tokens": None,
                    "total_duration_ns": None,
                    "load_duration_ns": None,
                    "prompt_eval_duration_ns": None,
                    "eval_duration_ns": None,
                    "output": None,
                    "raw_output": None,
                    "error": None,
                }

                if not article_text.strip():
                    item_result["error"] = (
                        "The article has no scraped text."
                    )

                else:
                    try:
                        prompt = build_prompt(article)

                        response = call_ollama(
                            model_name,
                            prompt,
                        )

                        item_result["prompt_tokens"] = (
                            response["prompt_tokens"]
                        )
                        item_result["output_tokens"] = (
                            response["output_tokens"]
                        )
                        item_result["total_duration_ns"] = (
                            response["total_duration_ns"]
                        )
                        item_result["load_duration_ns"] = (
                            response["load_duration_ns"]
                        )
                        item_result["prompt_eval_duration_ns"] = (
                            response["prompt_eval_duration_ns"]
                        )
                        item_result["eval_duration_ns"] = (
                            response["eval_duration_ns"]
                        )

                        raw_output = response["raw_output"]

                        try:
                            parsed_output = extract_json(raw_output)

                            validated_output = (
                                validate_generated_content(
                                    parsed_output
                                )
                            )

                            item_result["status"] = "success"
                            item_result["json_valid"] = True
                            item_result["output"] = validated_output

                        except Exception as error:
                            item_result["status"] = "invalid_output"
                            item_result["error"] = str(error)
                            item_result["raw_output"] = raw_output

                    except Exception as error:
                        item_result["status"] = "error"
                        item_result["error"] = (
                            f"{type(error).__name__}: {error}"
                        )

                item_result["elapsed_seconds"] = round(
                    time.time() - article_started, 3
                )

                if item_result["status"] == "success":
                    model_result["success_count"] += 1
                    print("Result: SUCCESS")
                else:
                    model_result["error_count"] += 1
                    print(
                        f"Result: {item_result['status']} - "
                        f"{item_result['error']}"
                    )

                model_result["results"].append(item_result)

                # Save after every article so partial results survive.
                save_json(results)

            model_result["status"] = (
                "completed_with_errors"
                if model_result["error_count"] > 0
                else "completed"
            )
            model_result["finished_at"] = utc_now()
            model_result["elapsed_seconds"] = round(
                time.time() - model_started, 3
            )

            save_json(results)

    except Exception as error:
        results["test_metadata"]["fatal_error"] = (
            f"{type(error).__name__}: {error}"
        )
        raise

    finally:
        results["test_metadata"]["finished_at"] = utc_now()
        results["test_metadata"]["elapsed_seconds"] = round(
            time.time() - run_started, 3
        )

        save_json(results)

        # Stop only the Ollama server started by this script.
        if server_process is not None:
            server_process.terminate()

            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

        print("\n" + "=" * 60)
        print("TEST FINISHED")
        print("=" * 60)
        print(f"Output file: {OUTPUT_FILE}")

        for model_name, model_result in (
            results["model_results"].items()
        ):
            print(
                f"{model_name}: "
                f"{model_result['success_count']} successful, "
                f"{model_result['error_count']} errors"
            )


if __name__ == "__main__":
    main()

