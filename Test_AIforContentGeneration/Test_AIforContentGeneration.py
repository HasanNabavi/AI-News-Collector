
import json
import os
import time
import urllib.request
import subprocess
import shutil
import platform
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

MODEL = "qwen3:4b"
ARTICLES_PER_MODEL = 1

# Allow up to two hours for one generation request.
REQUEST_TIMEOUT_SECONDS = 7200

MODEL_PULL_TIMEOUT_SECONDS = 1800
SERVER_START_TIMEOUT_SECONDS = 60

THINKING_ENABLED = True
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

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:
        result = json.loads(text[start:end + 1])
        if isinstance(result, dict):
            return result

    raise ValueError("The model did not return a valid JSON object.")


def format_duration(seconds):
    return f"{seconds:.2f} seconds"


def run_command(command, timeout=15):
    """Run a diagnostic command without failing the whole test."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()

        return {
            "available": result.returncode == 0,
            "return_code": result.returncode,
            "output": output[:12000],
            "error": error[:3000] if error else None,
        }

    except FileNotFoundError:
        return {
            "available": False,
            "error": "Command not found",
        }

    except Exception as error:
        return {
            "available": False,
            "error": f"{type(error).__name__}: {error}",
        }


# ============================================================
# Runner resource diagnostics
# ============================================================

def read_meminfo():
    """Read Linux RAM information in bytes."""

    result = {}

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            for line in file:
                parts = line.split()

                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    result[key] = int(parts[1]) * 1024

    except Exception as error:
        return {
            "error": f"{type(error).__name__}: {error}"
        }

    wanted = [
        "MemTotal",
        "MemAvailable",
        "MemFree",
        "Buffers",
        "Cached",
        "SwapTotal",
        "SwapFree",
    ]

    return {
        key: result[key]
        for key in wanted
        if key in result
    }


def read_cpu_model():
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as file:
            for line in file:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass

    return None


def read_disk_info():
    try:
        usage = shutil.disk_usage("/")
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        }
    except Exception as error:
        return {"error": str(error)}


def collect_runner_diagnostics():
    print("\n" + "=" * 60, flush=True)
    print("RUNNER RESOURCE DIAGNOSTICS", flush=True)
    print("=" * 60, flush=True)

    diagnostics = {
        "captured_at": utc_now(),
        "platform": platform.platform(),
        "operating_system": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
        "cpu_model": read_cpu_model(),
        "ram": read_meminfo(),
        "disk": read_disk_info(),
        "lscpu": run_command(["lscpu"]),
        "gpu_nvidia_smi": run_command(
            ["nvidia-smi"],
            timeout=15,
        ),
        "gpu_rocm_smi": run_command(
            ["rocm-smi"],
            timeout=15,
        ),
        "gpu_lspci": run_command(
            ["bash", "-lc", "lspci | grep -Ei 'vga|3d|display'"],
            timeout=15,
        ),
        "ollama_ps": run_command(["ollama", "ps"]),
        "ollama_version": run_command(["ollama", "--version"]),
    }

    print(f"Platform: {diagnostics['platform']}", flush=True)
    print(
        f"Logical CPU count: {diagnostics['logical_cpu_count']}",
        flush=True,
    )
    print(f"CPU model: {diagnostics['cpu_model']}", flush=True)

    ram = diagnostics["ram"]
    if "MemTotal" in ram:
        print(
            f"Total RAM: {ram['MemTotal'] / (1024 ** 3):.2f} GiB",
            flush=True,
        )
        if "MemAvailable" in ram:
            print(
                "Available RAM: "
                f"{ram['MemAvailable'] / (1024 ** 3):.2f} GiB",
                flush=True,
            )

    disk = diagnostics["disk"]
    if "total_bytes" in disk:
        print(
            f"Root filesystem free space: "
            f"{disk['free_bytes'] / (1024 ** 3):.2f} GiB",
            flush=True,
        )

    nvidia = diagnostics["gpu_nvidia_smi"]
    if nvidia["available"]:
        print("[GPU] NVIDIA GPU detected.", flush=True)
        print(nvidia["output"], flush=True)
    else:
        print(
            "[GPU] nvidia-smi unavailable. "
            "This alone does not prove that no GPU exists.",
            flush=True,
        )
        print(
            f"nvidia-smi result: {nvidia.get('error')}",
            flush=True,
        )

    rocm = diagnostics["gpu_rocm_smi"]
    if rocm["available"]:
        print("[GPU] AMD GPU tooling detected.", flush=True)
        print(rocm["output"], flush=True)

    lspci = diagnostics["gpu_lspci"]
    if lspci["available"] and lspci.get("output"):
        print("[GPU/Display devices]", flush=True)
        print(lspci["output"], flush=True)

    print("[OLLAMA PS BEFORE GENERATION]", flush=True)
    print(
        diagnostics["ollama_ps"].get("output")
        or diagnostics["ollama_ps"].get("error")
        or "No output",
        flush=True,
    )

    return diagnostics


def collect_runtime_snapshot(label):
    """Capture RAM and Ollama process/model status."""

    snapshot = {
        "label": label,
        "captured_at": utc_now(),
        "ram": read_meminfo(),
        "ollama_ps": run_command(["ollama", "ps"]),
    }

    print(f"\n[RESOURCE SNAPSHOT] {label}", flush=True)

    ram = snapshot["ram"]
    if "MemTotal" in ram and "MemAvailable" in ram:
        used = ram["MemTotal"] - ram["MemAvailable"]
        print(
            f"RAM used (estimated): {used / (1024 ** 3):.2f} GiB",
            flush=True,
        )
        print(
            f"RAM available: "
            f"{ram['MemAvailable'] / (1024 ** 3):.2f} GiB",
            flush=True,
        )

    print(
        snapshot["ollama_ps"].get("output")
        or snapshot["ollama_ps"].get("error")
        or "No Ollama process information",
        flush=True,
    )

    return snapshot


# ============================================================
# Ollama connection and model setup
# ============================================================

def ollama_is_running():
    try:
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/tags",
            method="GET",
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200

    except Exception:
        return False


def start_ollama_if_needed():
    if ollama_is_running():
        print("[OLLAMA] Server is already running.", flush=True)
        return None

    executable = shutil.which("ollama")

    if not executable:
        raise RuntimeError("Ollama executable was not found in PATH.")

    print("[OLLAMA] Starting server...", flush=True)

    process = subprocess.Popen(
        [executable, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if ollama_is_running():
            print("[OLLAMA] Server is ready.", flush=True)
            return process

        if process.poll() is not None:
            raise RuntimeError("Ollama server stopped unexpectedly.")

        time.sleep(2)

    process.terminate()

    raise RuntimeError(
        "Ollama server did not become ready within "
        f"{SERVER_START_TIMEOUT_SECONDS} seconds."
    )


def ensure_model_available(model_name):
    print(f"[MODEL] Checking model: {model_name}", flush=True)

    executable = shutil.which("ollama")

    if not executable:
        raise RuntimeError("Ollama executable was not found.")

    started = time.monotonic()

    try:
        result = subprocess.run(
            [executable, "pull", model_name],
            capture_output=True,
            text=True,
            timeout=MODEL_PULL_TIMEOUT_SECONDS,
            check=False,
        )

    except subprocess.TimeoutExpired as error:
        raise TimeoutError(
            "Model setup timed out after "
            f"{MODEL_PULL_TIMEOUT_SECONDS} seconds."
        ) from error

    elapsed = time.monotonic() - started

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"Failed to prepare model {model_name}."
        )

    print(
        f"[MODEL] Ready: {model_name} "
        f"({format_duration(elapsed)})",
        flush=True,
    )


# ============================================================
# Prompt construction
# ============================================================

def build_prompt(article):
    title = article.get("title", "")
    source = article.get("source", "")
    category = article.get("category", "")
    article_text = get_article_text(article)

    return f"""
You are a careful Persian-language news editor.

Turn the original news article below into a short,
accurate, readable Persian news item.

IMPORTANT RULES:
1. Use only facts explicitly supported by the article.
2. Do not invent names, numbers, dates, quotes, causes,
   or conclusions.
3. Do not guess when information is uncertain or absent.
4. Preserve factual meaning and nuance.
5. Write natural, clear Persian for a general audience.
6. Avoid awkward word-for-word translation.
7. The headline must be concise and informative.
8. The short_text should usually contain 2 to 4 short
   Persian sentences.
9. Provide 3 to 5 concise key points in Persian.
10. Do not add commentary, opinions, or a source list.
11. Return only one valid JSON object.
12. All generated content must be in Persian.
13. Each key point must contain a distinct fact.
14. Do not repeat the short_text as key points.
15. Do not combine separate events or imply a causal
    relationship unless the article explicitly supports it.

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


# ============================================================
# Ollama generation request
# ============================================================

def call_ollama(model_name, prompt):
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "think": THINKING_ENABLED,
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
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    request_started = time.monotonic()

    print(
        f"[REQUEST START] Model={model_name} "
        f"Time={utc_now()} "
        f"Timeout={REQUEST_TIMEOUT_SECONDS}s "
        f"Think={THINKING_ENABLED}",
        flush=True,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response_body = response.read()

        elapsed = time.monotonic() - request_started
        response_data = json.loads(response_body.decode("utf-8"))

    except Exception as error:
        elapsed = time.monotonic() - request_started

        print(
            f"[REQUEST FAILED] Model={model_name} "
            f"Elapsed={format_duration(elapsed)} "
            f"Error={type(error).__name__}: {error}",
            flush=True,
        )
        raise

    message = response_data.get("message", {})
    raw_output = message.get("content", "") or ""
    thinking_output = message.get("thinking", "") or ""

    print(
        f"[REQUEST END] Model={model_name} "
        f"Elapsed={format_duration(elapsed)} "
        f"Time={utc_now()} "
        f"ContentChars={len(raw_output)} "
        f"ThinkingChars={len(thinking_output)}",
        flush=True,
    )

    if not raw_output.strip():
        raise ValueError(
            "Ollama returned empty content. "
            f"Thinking characters: {len(thinking_output)}"
        )

    return {
        "raw_output": raw_output,
        "thinking_output": thinking_output,
        "request_elapsed_seconds": round(elapsed, 3),
        "prompt_tokens": response_data.get("prompt_eval_count"),
        "output_tokens": response_data.get("eval_count"),
        "total_duration_ns": response_data.get("total_duration"),
        "load_duration_ns": response_data.get("load_duration"),
        "prompt_eval_duration_ns": response_data.get(
            "prompt_eval_duration"
        ),
        "eval_duration_ns": response_data.get("eval_duration"),
        "done_reason": response_data.get("done_reason"),
    }


# ============================================================
# Output validation
# ============================================================

def validate_generated_content(content):
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
        "key_points": [point.strip() for point in key_points],
    }


# ============================================================
# Main test
# ============================================================

def main():
    run_started = time.monotonic()
    started_at = utc_now()

    print("=" * 60, flush=True)
    print("QWEN THINKING MODE RESOURCE TEST", flush=True)
    print("=" * 60, flush=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        input_data = json.load(file)

    articles = input_data.get("news", [])

    if not isinstance(articles, list):
        raise ValueError("Input JSON must contain a 'news' list.")

    if not articles:
        raise ValueError("The input file contains no news articles.")

    # Exactly one complete article; no text truncation.
    articles = articles[:ARTICLES_PER_MODEL]

    article = articles[0]
    article_text = get_article_text(article)

    print(f"Input file: {INPUT_FILE}", flush=True)
    print(f"Selected articles: {len(articles)}", flush=True)
    print(f"Model: {MODEL}", flush=True)
    print(f"Thinking enabled: {THINKING_ENABLED}", flush=True)
    print(
        f"Request timeout: {REQUEST_TIMEOUT_SECONDS} seconds",
        flush=True,
    )
    print(
        f"Original text length: {len(article_text)} characters",
        flush=True,
    )

    results = {
        "test_metadata": {
            "test_name": "Test_AIforContentGeneration",
            "purpose": (
                "One-article Qwen3 test with thinking enabled, "
                "two-hour request timeout, and runner diagnostics."
            ),
            "model": MODEL,
            "think": THINKING_ENABLED,
            "temperature": 0.2,
            "articles_per_model": len(articles),
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "started_at": started_at,
            "finished_at": None,
            "elapsed_seconds": None,
        },
        "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
        "output_file": str(OUTPUT_FILE.relative_to(PROJECT_DIR)),
        "article_count": len(articles),
        "runner_diagnostics": None,
        "runtime_snapshots": [],
        "articles": [
            {
                "article_index": 0,
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "category": article.get("category", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at"),
                "group_id": article.get("group_id"),
                "original_text_characters": len(article_text),
                **(
                    {"original_text": article_text}
                    if SAVE_ORIGINAL_TEXT else {}
                ),
            }
        ],
        "model_results": {},
    }

    save_json(results)
    server_process = None

    model_result = {
        "model": MODEL,
        "status": "running",
        "think": THINKING_ENABLED,
        "started_at": utc_now(),
        "finished_at": None,
        "elapsed_seconds": None,
        "success_count": 0,
        "error_count": 0,
        "results": [],
    }
    results["model_results"][MODEL] = model_result
    save_json(results)

    try:
        # Capture runner hardware before model setup and generation.
        results["runner_diagnostics"] = collect_runner_diagnostics()
        save_json(results)

        server_process = start_ollama_if_needed()

        ensure_model_available(MODEL)

        # Capture the model placement before generation.
        results["runtime_snapshots"].append(
            collect_runtime_snapshot("before_generation")
        )
        save_json(results)

        title = article.get("title", "")
        print(f"\n[ARTICLE] {title}", flush=True)

        article_started = time.monotonic()

        item_result = {
            "article_index": 0,
            "original_title": title,
            "status": "error",
            "started_at": utc_now(),
            "finished_at": None,
            "elapsed_seconds": None,
            "json_valid": False,
            "prompt_tokens": None,
            "output_tokens": None,
            "request_elapsed_seconds": None,
            "total_duration_ns": None,
            "load_duration_ns": None,
            "prompt_eval_duration_ns": None,
            "eval_duration_ns": None,
            "done_reason": None,
            "output": None,
            "raw_output": None,
            "thinking_output": None,
            "error": None,
        }

        if not article_text.strip():
            item_result["error"] = "The article has no scraped text."

        else:
            try:
                response = call_ollama(
                    MODEL,
                    build_prompt(article),
                )

                item_result["prompt_tokens"] = response["prompt_tokens"]
                item_result["output_tokens"] = response["output_tokens"]
                item_result["request_elapsed_seconds"] = (
                    response["request_elapsed_seconds"]
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
                item_result["done_reason"] = response["done_reason"]
                item_result["thinking_output"] = (
                    response["thinking_output"]
                )

                raw_output = response["raw_output"]

                try:
                    parsed_output = extract_json(raw_output)
                    validated_output = validate_generated_content(
                        parsed_output
                    )

                    item_result["status"] = "success"
                    item_result["json_valid"] = True
                    item_result["output"] = validated_output

                except Exception as error:
                    item_result["status"] = "invalid_output"
                    item_result["error"] = (
                        f"{type(error).__name__}: {error}"
                    )
                    item_result["raw_output"] = raw_output

            except Exception as error:
                item_result["status"] = "error"
                item_result["error"] = (
                    f"{type(error).__name__}: {error}"
                )

        item_result["finished_at"] = utc_now()
        item_result["elapsed_seconds"] = round(
            time.monotonic() - article_started,
            3,
        )

        if item_result["status"] == "success":
            model_result["success_count"] = 1
            print(
                f"[RESULT] SUCCESS | "
                f"Elapsed={item_result['elapsed_seconds']}s",
                flush=True,
            )
        else:
            model_result["error_count"] = 1
            print(
                f"[RESULT] {item_result['status']} | "
                f"Elapsed={item_result['elapsed_seconds']}s | "
                f"Error={item_result['error']}",
                flush=True,
            )

        model_result["results"].append(item_result)
        save_json(results)

        # Capture RAM and Ollama model placement after generation.
        results["runtime_snapshots"].append(
            collect_runtime_snapshot("after_generation")
        )

        model_result["status"] = (
            "completed"
            if model_result["error_count"] == 0
            else "completed_with_errors"
        )

    except Exception as error:
        model_result["status"] = "test_failed"
        model_result["setup_error"] = (
            f"{type(error).__name__}: {error}"
        )
        results["test_metadata"]["fatal_error"] = (
            f"{type(error).__name__}: {error}"
        )
        raise

    finally:
        model_result["finished_at"] = utc_now()
        model_result["elapsed_seconds"] = round(
            time.monotonic() - run_started,
            3,
        )

        results["test_metadata"]["finished_at"] = utc_now()
        results["test_metadata"]["elapsed_seconds"] = round(
            time.monotonic() - run_started,
            3,
        )

        save_json(results)

        if server_process is not None:
            print(
                "[OLLAMA] Stopping server started by this script...",
                flush=True,
            )

            server_process.terminate()

            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

        print("\n" + "=" * 60, flush=True)
        print("TEST FINISHED", flush=True)
        print(f"Output file: {OUTPUT_FILE}", flush=True)
        print(
            f"Successes: {model_result['success_count']} | "
            f"Errors: {model_result['error_count']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
