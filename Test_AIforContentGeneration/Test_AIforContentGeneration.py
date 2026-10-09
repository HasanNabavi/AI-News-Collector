
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
# Utilities
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(data):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_article_text(article):
    scraped_data = article.get("scraped_data", {})

    if isinstance(scraped_data, dict):
        nested = scraped_data.get("scraped_data", {})

        if isinstance(nested, dict):
            text = nested.get("text", "")
            if text:
                return str(text).strip()

        text = scraped_data.get("text", "")
        if text:
            return str(text).strip()

    return str(article.get("text", "")).strip()


def extract_json(text):
    text = str(text).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])

    raise ValueError("پاسخ مدل شامل JSON معتبر نیست.")


def validate_news_output(data):
    if not isinstance(data, dict):
        raise ValueError("خروجی باید یک شیء JSON باشد.")

    for field in ("title", "text"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"فیلد {field} خالی یا نامعتبر است.")

    return data


def sum_tokens(usage):
    if not isinstance(usage, dict):
        return 0
    return int(usage.get("total_tokens") or 0)


# ============================================================
# OpenRouter API
# ============================================================

def call_model(messages):
    if not API_KEY:
        raise RuntimeError(
            "متغیر OPENROUTER_API_KEY تنظیم نشده است."
        )

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
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

    started = time.time()

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            status_code = response.status
            response_text = response.read().decode("utf-8")

    except urllib.error.HTTPError as error:
        error_text = error.read().decode(
            "utf-8", errors="replace"
        )
        raise RuntimeError(
            f"خطای HTTP {error.code}: {error_text[:1500]}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"خطا در اتصال به OpenRouter: {error.reason}"
        ) from error

    except TimeoutError as error:
        raise RuntimeError(
            f"مهلت {REQUEST_TIMEOUT_SECONDS} ثانیه‌ای درخواست تمام شد."
        ) from error

    elapsed = round(time.time() - started, 2)

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"پاسخ API JSON معتبر نیست: {response_text[:1000]}"
        ) from error

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(
            f"پاسخ API فاقد choices است: {response_text[:1000]}"
        )

    choice = choices[0]
    message = choice.get("message", {})
    content = message.get("content", "")

    if isinstance(content, list):
        content = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )

    content = str(content).strip()

    if not content:
        raise RuntimeError("مدل پاسخ متنی خالی برگرداند.")

    usage = data.get("usage", {})

    return {
        "content": content,
        "elapsed_seconds": elapsed,
        "http_status": status_code,
        "usage": usage,
        "total_tokens": sum_tokens(usage),
        "finish_reason": choice.get("finish_reason"),
    }


# ============================================================
# Prompts
# ============================================================

def prompt_direct_persian(article, article_text):
    return [
        {
            "role": "system",
            "content": (
                "تو دبیر حرفه‌ای یک کانال خبری فارسی درباره هوش مصنوعی، "
                "رباتیک و فناوری‌های آینده هستی. از متن اصلی مقاله، "
                "یک خبر کوتاه، دقیق، روان و جذاب به فارسی بنویس. "
                "هیچ واقعیتی را اختراع نکن. عنوان اصلی فقط اطلاعات "
                "کمکی برای شناسایی موضوع است و به‌تنهایی مدرک factual "
                "محسوب نمی‌شود. خروجی فقط JSON معتبر با دو فیلد "
                "title و text باشد؛ بدون توضیح اضافی."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "original_title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "category": article.get("category", ""),
                    "article_text": article_text,
                },
                ensure_ascii=False,
            ),
        },
    ]


def prompt_english_draft(article, article_text):
    return [
        {
            "role": "system",
            "content": (
                "Write a concise English news brief using only facts "
                "explicitly supported by the article text. Do not invent "
                "details. Treat the headline as metadata, not evidence. "
                "Return only valid JSON with fields title and text."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "original_title": article.get("title", ""),
                    "article_text": article_text,
                },
                ensure_ascii=False,
            ),
        },
    ]


def prompt_persian_from_english(english_draft):
    return [
        {
            "role": "system",
            "content": (
                "پیش‌نویس انگلیسی را به یک خبر کوتاه و روان فارسی تبدیل کن. "
                "ترجمه طبیعی باشد، نه کلمه‌به‌کلمه. واقعیت جدید اضافه نکن. "
                "خروجی فقط JSON معتبر با فیلدهای title و text باشد."
            ),
        },
        {
            "role": "user",
            "content": english_draft,
        },
    ]


def prompt_extract_facts(article, article_text):
    return [
        {
            "role": "system",
            "content": (
                "Extract only facts explicitly stated in the article text. "
                "Do not infer missing details. The headline is metadata, "
                "not evidence. Return only valid JSON with fields: "
                "main_event, organizations, people, numbers, dates, "
                "location, technical_details, uncertainties. "
                "Use empty strings or arrays when information is absent."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "original_title": article.get("title", ""),
                    "article_text": article_text,
                },
                ensure_ascii=False,
            ),
        },
    ]


def prompt_persian_from_facts(facts):
    return [
        {
            "role": "system",
            "content": (
                "بر اساس واقعیت‌های استخراج‌شده، یک خبر کوتاه و روان "
                "به فارسی بنویس. فقط از اطلاعات موجود در JSON استفاده کن؛ "
                "چیزی را حدس نزن. خروجی فقط JSON معتبر با فیلدهای "
                "title و text باشد."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(facts, ensure_ascii=False),
        },
    ]


# ============================================================
# Shared result helpers
# ============================================================

def stage_info(name, response):
    return {
        "name": name,
        "elapsed_seconds": response["elapsed_seconds"],
        "tokens": response["total_tokens"],
        "finish_reason": response["finish_reason"],
    }


def error_result(started, request_count, total_tokens, error, stages=None):
    return {
        "status": "error",
        "request_count": request_count,
        "wall_clock_elapsed_seconds": round(time.time() - started, 2),
        "total_tokens": total_tokens,
        "stages": stages or [],
        "error": str(error),
    }


# ============================================================
# Method 1: Direct Persian generation
# ============================================================

def run_method_1(article, article_text):
    started = time.time()
    request_count = 0
    total_tokens = 0
    stages = []

    try:
        request_count += 1
        response = call_model(
            prompt_direct_persian(article, article_text)
        )
        total_tokens += response["total_tokens"]
        stages.append(stage_info("direct_persian", response))

        output = validate_news_output(
            extract_json(response["content"])
        )

        return {
            "status": "success",
            "request_count": request_count,
            "wall_clock_elapsed_seconds": round(time.time() - started, 2),
            "total_tokens": total_tokens,
            "stages": stages,
            "output": output,
        }

    except Exception as error:
        return error_result(
            started, request_count, total_tokens, error, stages
        )


# ============================================================
# Method 2: English draft, then Persian adaptation
# ============================================================

def run_method_2(article, article_text):
    started = time.time()
    request_count = 0
    total_tokens = 0
    stages = []

    try:
        request_count += 1
        first = call_model(
            prompt_english_draft(article, article_text)
        )
        total_tokens += first["total_tokens"]
        stages.append(stage_info("english_draft", first))

        english_draft = extract_json(first["content"])
        if not isinstance(english_draft, dict):
            raise ValueError("پیش‌نویس انگلیسی JSON معتبر نیست.")

        request_count += 1
        second = call_model(
            prompt_persian_from_english(
                json.dumps(english_draft, ensure_ascii=False)
            )
        )
        total_tokens += second["total_tokens"]
        stages.append(stage_info("persian_adaptation", second))

        output = validate_news_output(
            extract_json(second["content"])
        )

        return {
            "status": "success",
            "request_count": request_count,
            "wall_clock_elapsed_seconds": round(time.time() - started, 2),
            "total_tokens": total_tokens,
            "stages": stages,
            "english_draft": english_draft,
            "output": output,
        }

    except Exception as error:
        return error_result(
            started, request_count, total_tokens, error, stages
        )


# ============================================================
# Method 3: Fact extraction, then Persian generation
# ============================================================

def run_method_3(article, article_text):
    started = time.time()
    request_count = 0
    total_tokens = 0
    stages = []

    try:
        request_count += 1
        first = call_model(
            prompt_extract_facts(article, article_text)
        )
        total_tokens += first["total_tokens"]
        stages.append(stage_info("fact_extraction", first))

        facts = extract_json(first["content"])
        if not isinstance(facts, dict):
            raise ValueError("خروجی استخراج واقعیت‌ها معتبر نیست.")

        request_count += 1
        second = call_model(
            prompt_persian_from_facts(facts)
        )
        total_tokens += second["total_tokens"]
        stages.append(stage_info("persian_generation", second))

        output = validate_news_output(
            extract_json(second["content"])
        )

        return {
            "status": "success",
            "request_count": request_count,
            "wall_clock_elapsed_seconds": round(time.time() - started, 2),
            "total_tokens": total_tokens,
            "stages": stages,
            "extracted_facts": facts,
            "output": output,
        }

    except Exception as error:
        return error_result(
            started, request_count, total_tokens, error, stages
        )


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("AI Content Generation Test")
    print(f"Model: {MODEL}")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 60)

    if not API_KEY:
        raise RuntimeError(
            "کلید API تنظیم نشده است. "
            "وجود Secret با نام OPENROUTER_API_KEY را بررسی کن."
        )

    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"فایل ورودی پیدا نشد: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        input_data = json.load(file)

    if isinstance(input_data, list):
        articles = input_data
    elif isinstance(input_data, dict):
        articles = input_data.get("articles", [])
        if not articles:
            articles = input_data.get("news", [])
    else:
        raise ValueError("ساختار فایل ورودی پشتیبانی نمی‌شود.")

    if not isinstance(articles, list) or not articles:
        raise ValueError("هیچ مقاله‌ای در فایل ورودی پیدا نشد.")

    articles = articles[:ARTICLES_PER_TEST]

    results = {
        "test_metadata": {
            "started_at": utc_now(),
            "model": MODEL,
            "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
            "output_file": str(OUTPUT_FILE.relative_to(PROJECT_DIR)),
            "article_limit": ARTICLES_PER_TEST,
        },
        "article_count": len(articles),
        "method_results": {},
    }

    save_json(results)

    methods = {
        "method_1_direct_persian": run_method_1,
        "method_2_english_then_persian": run_method_2,
        "method_3_facts_then_persian": run_method_3,
    }

    failed_methods = []

    for index, article in enumerate(articles, start=1):
        article_text = get_article_text(article)

        article_result = {
            "input_title": article.get("title", ""),
            "source": article.get("source", ""),
        }

        if SAVE_ORIGINAL_TEXT:
            article_result["original_text"] = article_text

        if not article_text:
            article_result["status"] = "skipped"
            article_result["error"] = "متن مقاله خالی است."
            results["method_results"][str(index)] = article_result
            save_json(results)
            failed_methods.append(f"article_{index}: متن مقاله خالی است")
            continue

        for method_name, method_function in methods.items():
            print(f"\nمقاله {index}: {method_name}")

            method_result = method_function(article, article_text)
            article_result[method_name] = method_result

            print(
                f"Status: {method_result.get('status')} | "
                f"Requests: {method_result.get('request_count')} | "
                f"Elapsed: "
                f"{method_result.get('wall_clock_elapsed_seconds')}s"
            )

            if method_result.get("error"):
                print(f"Error: {method_result['error']}")
                failed_methods.append(
                    f"article_{index}/{method_name}: "
                    f"{method_result['error']}"
                )

            results["method_results"][str(index)] = article_result
            save_json(results)

    results["test_metadata"]["finished_at"] = utc_now()
    results["test_metadata"]["failed_method_count"] = len(failed_methods)
    save_json(results)

    print("\nآزمایش تمام شد.")
    print(f"فایل خروجی: {OUTPUT_FILE}")

    if failed_methods:
        print("\nروش‌های ناموفق:")
        for failure in failed_methods:
            print(f"- {failure}")
        raise RuntimeError(
            f"{len(failed_methods)} مورد ناموفق بود. "
            "جزئیات در فایل خروجی ثبت شده است."
        )

    print("هر سه روش با موفقیت اجرا شدند.")


if __name__ == "__main__":
    main()
