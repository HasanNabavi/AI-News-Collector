
import json
import os
import re
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
MODEL = "google/gemma-4-26b-a4b-it:free"

ARTICLES_PER_TEST = 1
REQUEST_TIMEOUT_SECONDS = 180

# Token limits for each stage
ENGLISH_MAX_TOKENS = 900
PERSIAN_MAX_TOKENS = 1600

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
            raise ValueError(
                f"فیلد {field} خالی یا نامعتبر است."
            )

    return {
        "title": data["title"].strip(),
        "text": data["text"].strip(),
    }


def sum_tokens(usage):
    if not isinstance(usage, dict):
        return 0

    return int(usage.get("total_tokens") or 0)


def paragraph_count(text):
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text.strip())
        if p.strip()
    ]

    return len(paragraphs)


# ============================================================
# Persian quality checks
# ============================================================

def check_persian_quality(output):
    title = output["title"]
    text = output["text"]

    warnings = []

    count = paragraph_count(text)

    if count < 1 or count > 3:
        warnings.append(
            f"تعداد پاراگراف‌ها {count} است؛ "
            "انتظار می‌رود بین ۱ تا ۳ باشد."
        )

    allowed_phrases = {
        "OpenAI",
        "ChatGPT",
        "Hugging Face",
        "Google",
        "Microsoft",
        "Nvidia",
        "Figure AI",
        "Boston Dynamics",
        "Tesla",
        "DeepMind",
        "Anthropic",
        "AI",
        "AGI",
        "GPU",
        "CPU",
        "API",
        "NASA",
        "BBC",
        "CEO",
        "VVER-1000",
        "MELCOR",
        "RELAP5",
    }

    combined_text = f"{title}\n{text}"

    latin_words = re.findall(
        r"[A-Za-z][A-Za-z0-9.'’_-]*",
        combined_text,
    )

    consecutive_english = re.findall(
        r"\b[A-Za-z][A-Za-z'-]*"
        r"(?:\s+[A-Za-z][A-Za-z'-]*){1,5}\b",
        combined_text,
    )

    suspicious_phrases = []

    for phrase in consecutive_english:
        normalized = phrase.strip(" .,;:!?()[]{}\"'")

        if normalized in allowed_phrases:
            continue

        if normalized and normalized not in suspicious_phrases:
            suspicious_phrases.append(normalized)

    mixed_script = re.findall(
        r"\S*[A-Za-z]+\S*[\u0600-\u06FF]\S*|"
        r"\S*[\u0600-\u06FF]\S*[A-Za-z]+\S*",
        combined_text,
    )

    mixed_script = list(dict.fromkeys(mixed_script))

    if suspicious_phrases:
        warnings.append({
            "type": "possible_english_left_in_text",
            "items": suspicious_phrases,
        })

    if mixed_script:
        warnings.append({
            "type": "mixed_persian_english_tokens",
            "items": mixed_script,
        })

    return {
        "paragraph_count": count,
        "latin_word_count": len(latin_words),
        "warnings": warnings,
        "needs_manual_review": bool(warnings),
    }


# ============================================================
# OpenRouter API
# ============================================================

def call_model(messages, max_tokens):
    if not API_KEY:
        raise RuntimeError(
            "متغیر OPENROUTER_API_KEY تنظیم نشده است."
        )

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
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
    finish_reason = choice.get("finish_reason")
    usage = data.get("usage", {})

    if finish_reason == "length":
        usage_summary = {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "completion_tokens_details": usage.get(
                "completion_tokens_details"
            ),
        }

        raise RuntimeError(
            "پاسخ مدل به سقف توکن رسید و احتمالاً ناقص است. "
            f"Model={MODEL}; "
            f"max_tokens={max_tokens}; "
            f"finish_reason={finish_reason}; "
            f"usage={json.dumps(usage_summary, ensure_ascii=False)}"
        )

    if not content:
        raise RuntimeError(
            "مدل پاسخ متنی خالی برگرداند. "
            f"finish_reason={finish_reason}; "
            f"usage={json.dumps(usage, ensure_ascii=False)}"
        )

    return {
        "content": content,
        "elapsed_seconds": elapsed,
        "http_status": status_code,
        "usage": usage,
        "total_tokens": sum_tokens(usage),
        "finish_reason": finish_reason,
    }


# ============================================================
# Stage 1: English news generation
# ============================================================

def prompt_english_draft(article, article_text):
    return [
        {
            "role": "system",
            "content": (
                "You are a professional news editor covering AI, "
                "robotics, and future technology.\n"
                "Write a concise English news brief based only on "
                "the supplied article text.\n"
                "Requirements:\n"
                "- Focus on the main event and its most important facts.\n"
                "- Keep the brief suitable for a short Telegram news post.\n"
                "- Use 1 to 3 short paragraphs.\n"
                "- Do not invent facts, numbers, dates, quotes, or causes.\n"
                "- Preserve uncertainty and attribution from the source.\n"
                "- Do not treat the headline as evidence for extra claims.\n"
                "- Do not include unrelated recommendations or page metadata.\n"
                "- Return only valid JSON with one field: text.\n"
                "- Do not use Markdown or add explanations."
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


# ============================================================
# Stage 2: Faithful title translation + Persian news
# ============================================================

def prompt_persian_from_english(original_title, english_draft):
    return [
        {
            "role": "system",
            "content": (
                "تو ویراستار حرفه‌ای فارسی برای یک کانال خبری "
                "درباره هوش مصنوعی، رباتیک و فناوری‌های آینده هستی.\n\n"

                "وظیفه تو تولید خروجی نهایی با دو فیلد title و text است.\n\n"

                "قواعد عنوان:\n"
                "- عنوان اصلی انگلیسی را با ترجمه‌ای وفادار و نزدیک "
                "به متن اصلی به فارسی برگردان.\n"
                "- معنی، لحن و میزان قطعیت عنوان را حفظ کن.\n"
                "- عنوان تازه یا جذاب‌تر از خودت نساز.\n"
                "- نام شرکت‌ها و اشخاص را درست حفظ کن.\n\n"

                "قواعد متن خبر:\n"
                "- پیش‌نویس انگلیسی را به فارسی طبیعی و روان تبدیل کن.\n"
                "- متن نهایی باید فقط ۱ تا ۳ پاراگراف کوتاه داشته باشد.\n"
                "- جمله‌ها روشن، مختصر و مناسب انتشار در تلگرام باشند.\n"
                "- تمام جمله‌های متن خبری باید فارسی طبیعی باشند.\n"
                "- نام خاص یا اصطلاح فنی شناخته‌شده می‌تواند انگلیسی بماند؛ "
                "اما عبارت‌های معمول انگلیسی را به فارسی ترجمه کن.\n"
                "- هیچ واژه انگلیسی ناقص، عبارت تصادفی یا ترکیب خراب "
                "فارسی‌ـ‌انگلیسی باقی نگذار.\n"
                "- هیچ اطلاعات، عدد، نام، نقل‌قول یا ادعای جدیدی اضافه نکن.\n"
                "- ادعاها، انتساب‌ها و عدم قطعیت‌های متن انگلیسی را حفظ کن.\n"
                "- اطلاعات موجود در عنوان را به‌تنهایی مبنای افزودن "
                "واقعیت جدید به متن قرار نده.\n"
                "- ترجمه طبیعی باشد، نه ترجمه کلمه‌به‌کلمه.\n"
                "- متن را از نظر املا، دستور زبان و روانی بازبینی کن.\n\n"

                "خروجی فقط JSON معتبر با فیلدهای title و text باشد. "
                "از Markdown و توضیحات اضافی استفاده نکن."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "original_title_to_translate_faithfully":
                        original_title,
                    "english_news_draft": english_draft,
                },
                ensure_ascii=False,
            ),
        },
    ]


# ============================================================
# Method 2 only: English -> Persian
# ============================================================

def run_method_2(article, article_text):
    started = time.time()
    request_count = 0
    total_tokens = 0
    stages = []

    try:
        # Stage 1: English draft
        request_count += 1

        first = call_model(
            prompt_english_draft(article, article_text),
            max_tokens=ENGLISH_MAX_TOKENS,
        )

        total_tokens += first["total_tokens"]

        stages.append({
            "name": "english_draft",
            "elapsed_seconds": first["elapsed_seconds"],
            "tokens": first["total_tokens"],
            "finish_reason": first["finish_reason"],
            "usage": first["usage"],
        })

        english_data = extract_json(first["content"])

        if not isinstance(english_data, dict):
            raise ValueError(
                "پیش‌نویس انگلیسی JSON معتبر نیست."
            )

        english_draft = english_data.get("text", "")

        if not isinstance(english_draft, str) or not english_draft.strip():
            raise ValueError(
                "متن پیش‌نویس انگلیسی خالی یا نامعتبر است."
            )

        # Stage 2: Faithful Persian title + Persian text
        request_count += 1

        second = call_model(
            prompt_persian_from_english(
                article.get("title", ""),
                english_draft,
            ),
            max_tokens=PERSIAN_MAX_TOKENS,
        )

        total_tokens += second["total_tokens"]

        stages.append({
            "name": "persian_adaptation",
            "elapsed_seconds": second["elapsed_seconds"],
            "tokens": second["total_tokens"],
            "finish_reason": second["finish_reason"],
            "usage": second["usage"],
        })

        output = validate_news_output(
            extract_json(second["content"])
        )

        quality_checks = check_persian_quality(output)

        return {
            "status": "success",
            "request_count": request_count,
            "wall_clock_elapsed_seconds": round(
                time.time() - started, 2
            ),
            "total_tokens": total_tokens,
            "stages": stages,
            "english_draft": english_draft,
            "output": output,
            "quality_checks": quality_checks,
        }

    except Exception as error:
        return {
            "status": "error",
            "request_count": request_count,
            "wall_clock_elapsed_seconds": round(
                time.time() - started, 2
            ),
            "total_tokens": total_tokens,
            "stages": stages,
            "error": str(error),
        }


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("AI Content Generation Test - Method 2 only")
    print(f"Model: {MODEL}")
    print(f"English max tokens: {ENGLISH_MAX_TOKENS}")
    print(f"Persian max tokens: {PERSIAN_MAX_TOKENS}")
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
        raise ValueError(
            "ساختار فایل ورودی پشتیبانی نمی‌شود."
        )

    if not isinstance(articles, list) or not articles:
        raise ValueError(
            "هیچ مقاله‌ای در فایل ورودی پیدا نشد."
        )

    articles = articles[:ARTICLES_PER_TEST]

    results = {
        "test_metadata": {
            "started_at": utc_now(),
            "model": MODEL,
            "method": "method_2_english_then_persian",
            "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
            "output_file": str(OUTPUT_FILE.relative_to(PROJECT_DIR)),
            "article_limit": ARTICLES_PER_TEST,
        },
        "article_count": len(articles),
        "method_results": {},
    }

    save_json(results)
    failed_articles = []

    for index, article in enumerate(articles, start=1):
        article_text = get_article_text(article)

        article_result = {
            "input_title": article.get("title", ""),
            "source": article.get("source", ""),
        }

        if SAVE_ORIGINAL_TEXT:
            article_result["original_text"] = article_text

        if not article_text:
            article_result["method_2_english_then_persian"] = {
                "status": "error",
                "request_count": 0,
                "error": "متن مقاله خالی است.",
            }

            failed_articles.append(index)
            results["method_results"][str(index)] = article_result
            save_json(results)
            continue

        print(f"\nمقاله {index}: روش انگلیسی سپس فارسی")

        method_result = run_method_2(article, article_text)

        article_result["method_2_english_then_persian"] = method_result
        results["method_results"][str(index)] = article_result

        print(
            f"Status: {method_result.get('status')} | "
            f"Requests: {method_result.get('request_count')} | "
            f"Elapsed: "
            f"{method_result.get('wall_clock_elapsed_seconds')}s"
        )

        if method_result.get("error"):
            print(f"Error: {method_result['error']}")
            failed_articles.append(index)

        quality = method_result.get("quality_checks", {})

        if quality.get("warnings"):
            print("هشدارهای کنترل کیفیت:")
            print(
                json.dumps(
                    quality["warnings"],
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # Save after every article, including failed results
        save_json(results)

    results["test_metadata"]["finished_at"] = utc_now()
    results["test_metadata"]["failed_article_count"] = len(
        failed_articles
    )

    save_json(results)

    print("\nآزمایش تمام شد.")
    print(f"فایل خروجی: {OUTPUT_FILE}")

    if failed_articles:
        raise RuntimeError(
            f"{len(failed_articles)} مقاله ناموفق بود. "
            "جزئیات در فایل خروجی ثبت شده است."
        )

    print("تولید محتوا با روش دوم انجام شد.")


if __name__ == "__main__":
    main()
