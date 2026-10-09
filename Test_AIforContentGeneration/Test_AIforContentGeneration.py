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

# برای آزمایش مدل‌های دیگر، فقط این خط را تغییر بده.
MODEL = "nvidia/nemotron-3.5-lightning:free"

ARTICLES_PER_TEST = 1
REQUEST_TIMEOUT_SECONDS = 180
MAX_TOKENS = 256
TEMPERATURE = 0.1


# ============================================================
# Utilities
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(data):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_articles():
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"فایل ورودی پیدا نشد: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        articles = data

    elif isinstance(data, dict):
        articles = data.get("news", [])

        if not articles:
            articles = data.get("articles", [])

    else:
        raise ValueError(
            "ساختار فایل ورودی پشتیبانی نمی‌شود."
        )

    if not isinstance(articles, list):
        raise ValueError(
            "فهرست اخبار در فایل ورودی معتبر نیست."
        )

    valid_articles = [
        article
        for article in articles
        if isinstance(article, dict)
        and isinstance(article.get("title"), str)
        and article["title"].strip()
    ]

    if not valid_articles:
        raise ValueError(
            "هیچ خبری با عنوان معتبر در فایل ورودی پیدا نشد."
        )

    return valid_articles[:ARTICLES_PER_TEST]


# ============================================================
# Headline translation
# ============================================================

def translate_headline(original_title):
    if not API_KEY:
        raise RuntimeError(
            "متغیر OPENROUTER_API_KEY تنظیم نشده است."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "تو مترجم حرفه‌ای تیترهای خبری انگلیسی به فارسی هستی. "
                "وظیفه تو فقط ترجمه عنوان خبر به فارسی روان، طبیعی "
                "و دقیق است.\n"
                "قواعد:\n"
                "- فقط عنوان انگلیسی ارائه‌شده را ترجمه کن.\n"
                "- معنای دقیق، لحن و میزان قطعیت عنوان را حفظ کن.\n"
                "- هیچ اطلاعات یا ادعایی به عنوان اضافه نکن.\n"
                "- عنوان را جذاب‌تر، اغراق‌آمیز یا جنجالی‌تر نکن.\n"
                "- نام اشخاص، شرکت‌ها و محصولات را درست حفظ کن.\n"
                "- اصطلاحات تخصصی را با معادل رایج و دقیق فارسی ترجمه کن.\n"
                "- در صورت نیاز، نام خاص را به شکل اصلی نگه دار.\n"
                "- ترجمه باید برای مخاطب عمومی یک کانال خبری مناسب باشد.\n"
                "- عنوان را خلاصه یا بازنویسی آزاد نکن.\n"
                "- فقط عنوان نهایی فارسی را برگردان.\n"
                "- هیچ توضیح، تحلیل، مقدمه، گیومه یا قالب JSON اضافه نکن."
            ),
        },
        {
            "role": "user",
            "content": original_title.strip(),
        },
    ]

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "reasoning": {
            "enabled": False
        },
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
            "X-Title": "AI News Headline Translation Test",
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
            response_text = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as error:
        error_text = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"خطای HTTP {error.code}: {error_text[:2000]}"
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
            f"پاسخ API شامل JSON معتبر نیست: {response_text[:1500]}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"ساختار پاسخ API معتبر نیست: {response_text[:1500]}"
        )

    # ثبت دقیق خطاهای داخل پاسخ JSON، حتی اگر HTTP برابر 200 باشد.
    if data.get("error"):
        api_error = data["error"]

        raise RuntimeError(
            "خطای اعلام‌شده از طرف API: "
            + json.dumps(api_error, ensure_ascii=False)[:2000]
        )

    choices = data.get("choices", [])

    if not isinstance(choices, list) or not choices:
        raise RuntimeError(
            "پاسخ API فاقد choices است. "
            f"HTTP={status_code}; "
            f"Response={response_text[:2000]}"
        )

    choice = choices[0]

    if not isinstance(choice, dict):
        raise RuntimeError(
            f"ساختار اولین choice معتبر نیست: {choice!r}"
        )

    message = choice.get("message", {})

    if not isinstance(message, dict):
        message = {}

    content = message.get("content", "")

    # پشتیبانی از پاسخ‌هایی که محتوا را به شکل فهرست برمی‌گردانند.
    if isinstance(content, list):
        text_parts = []

        for part in content:
            if isinstance(part, dict):
                part_text = part.get("text", "")

                if isinstance(part_text, str):
                    text_parts.append(part_text)

        content = "".join(text_parts)

    if content is None:
        content = ""

    translated_title = (
        content if isinstance(content, str) else str(content)
    ).strip()

    finish_reason = choice.get("finish_reason")
    usage = data.get("usage", {})

    if not isinstance(usage, dict):
        usage = {}

    # اطلاعات تشخیصی برای بررسی دقیق اجرای بعدی.
    diagnostics = {
        "model_requested": MODEL,
        "model_returned": data.get("model"),
        "http_status": status_code,
        "finish_reason": finish_reason,
        "elapsed_seconds": elapsed,
        "usage": usage,
        "response_id": data.get("id"),
        "response_content": translated_title[:2000],
    }

    if finish_reason == "length":
        raise RuntimeError(
            "پاسخ مدل به سقف توکن رسید و احتمالاً ناقص است. "
            + json.dumps(diagnostics, ensure_ascii=False)
        )

    if not translated_title:
        raise RuntimeError(
            "مدل عنوان ترجمه‌شده‌ای برنگرداند. "
            + json.dumps(diagnostics, ensure_ascii=False)
        )

    return {
        "translated_title": translated_title,
        "elapsed_seconds": elapsed,
        "http_status": status_code,
        "usage": usage,
        "total_tokens": int(usage.get("total_tokens") or 0),
        "finish_reason": finish_reason,
        "model_returned": data.get("model"),
        "response_id": data.get("id"),
    }


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("AI News Headline Translation Test")
    print(f"Model: {MODEL}")
    print(f"Max tokens: {MAX_TOKENS}")
    print("Reasoning: disabled")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 60)

    if not API_KEY:
        raise RuntimeError(
            "کلید API تنظیم نشده است. "
            "وجود Secret با نام OPENROUTER_API_KEY را بررسی کن."
        )

    articles = load_articles()

    results = {
        "test_metadata": {
            "started_at": utc_now(),
            "model": MODEL,
            "method": "headline_translation_en_to_fa",
            "input_file": str(INPUT_FILE.relative_to(PROJECT_DIR)),
            "output_file": str(OUTPUT_FILE.relative_to(PROJECT_DIR)),
            "article_limit": ARTICLES_PER_TEST,
            "reasoning_enabled": False,
        },
        "article_count": len(articles),
        "translation_results": {},
    }

    save_json(results)
    failed_articles = []

    for index, article in enumerate(articles, start=1):
        original_title = article["title"].strip()

        article_result = {
            "input_title": original_title,
            "source": article.get("source", ""),
            "url": article.get("url", ""),
        }

        print(f"\nخبر {index}:")
        print(f"عنوان اصلی: {original_title}")

        try:
            translation = translate_headline(original_title)

            article_result.update({
                "status": "success",
                "translated_title": translation["translated_title"],
                "elapsed_seconds": translation["elapsed_seconds"],
                "http_status": translation["http_status"],
                "usage": translation["usage"],
                "total_tokens": translation["total_tokens"],
                "finish_reason": translation["finish_reason"],
                "model_returned": translation["model_returned"],
                "response_id": translation["response_id"],
            })

            print(
                f"عنوان فارسی: {translation['translated_title']}"
            )
            print(
                f"زمان اجرا: {translation['elapsed_seconds']} ثانیه"
            )
            print(
                f"توکن مصرف‌شده: {translation['total_tokens']}"
            )
            print(
                f"دلیل پایان پاسخ: {translation['finish_reason']}"
            )

        except Exception as error:
            article_result.update({
                "status": "error",
                "error": str(error),
            })

            failed_articles.append(index)
            print(f"خطا: {error}")

        results["translation_results"][str(index)] = article_result

        # ذخیره بعد از پردازش هر خبر، حتی در صورت شکست.
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
            f"{len(failed_articles)} ترجمه ناموفق بود. "
            "جزئیات در فایل خروجی ثبت شده است."
        )

    print("ترجمه عنوان با موفقیت انجام شد.")


if __name__ == "__main__":
    main()
