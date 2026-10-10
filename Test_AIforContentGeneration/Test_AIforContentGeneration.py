
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

# سه مدل برای مقایسه روی دقیقاً همان ۱۰ عنوان
MODELS = {
    "nemotron": "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen": "qwen/qwen3.8-27b:free",
    "gemma": "google/gemma-4-31b-it:free",
}

ARTICLES_PER_TEST = 10
REQUEST_TIMEOUT_SECONDS = 180
MAX_TOKENS = 256
TEMPERATURE = 0.1

# فاصله بین درخواست‌ها برای کاهش احتمال برخورد با محدودیت نرخ
SECONDS_BETWEEN_REQUESTS = 3.2


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

    if len(valid_articles) < ARTICLES_PER_TEST:
        raise ValueError(
            f"برای تست به {ARTICLES_PER_TEST} خبر نیاز است، "
            f"اما فقط {len(valid_articles)} خبر معتبر پیدا شد."
        )

    # همان ۱۰ خبر اول فایل F1 برای هر سه مدل استفاده می‌شوند.
    return valid_articles[:ARTICLES_PER_TEST]


# ============================================================
# Headline translation
# ============================================================

def translate_headline(original_title, model_id):
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
        "model": model_id,
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
            "X-Title": "AI News Headline Translation Comparison",
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
            f"HTTP {error.code}: {error_text[:2000]}"
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
            "پاسخ API شامل JSON معتبر نیست: "
            f"{response_text[:1500]}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            f"ساختار پاسخ API معتبر نیست: {response_text[:1500]}"
        )

    if data.get("error"):
        raise RuntimeError(
            "خطای اعلام‌شده از طرف API: "
            + json.dumps(
                data["error"],
                ensure_ascii=False,
            )[:2000]
        )

    choices = data.get("choices", [])

    if not isinstance(choices, list) or not choices:
        raise RuntimeError(
            f"پاسخ API فاقد choices است. HTTP={status_code}; "
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
            if (
                isinstance(part, dict)
                and isinstance(part.get("text"), str)
            ):
                text_parts.append(part["text"])

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

    diagnostics = {
        "model_requested": model_id,
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
        "status": "success",
        "model_requested": model_id,
        "model_returned": data.get("model"),
        "translated_title": translated_title,
        "elapsed_seconds": elapsed,
        "http_status": status_code,
        "usage": usage,
        "total_tokens": int(usage.get("total_tokens") or 0),
        "finish_reason": finish_reason,
        "response_id": data.get("id"),
    }


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 72)
    print("AI News Headline Translation Comparison")
    print(f"Models: {json.dumps(MODELS, ensure_ascii=False)}")
    print(f"Articles: {ARTICLES_PER_TEST}")
    print(f"Maximum output tokens per request: {MAX_TOKENS}")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 72)

    if not API_KEY:
        raise RuntimeError(
            "کلید API تنظیم نشده است. "
            "وجود Secret با نام OPENROUTER_API_KEY را بررسی کن."
        )

    articles = load_articles()

    results = {
        "test_metadata": {
            "started_at": utc_now(),
            "models": MODELS,

            # برای سازگاری با اعتبارسنج فعلی workflow
            "model": "multiple_models",

            "method": "headline_translation_en_to_fa",
            "input_file": str(
                INPUT_FILE.relative_to(PROJECT_DIR)
            ),
            "output_file": str(
                OUTPUT_FILE.relative_to(PROJECT_DIR)
            ),
            "article_limit": ARTICLES_PER_TEST,
            "model_count": len(MODELS),
            "expected_translation_count": (
                len(articles) * len(MODELS)
            ),
            "reasoning_enabled": False,
            "seconds_between_requests": SECONDS_BETWEEN_REQUESTS,
        },
        "article_count": len(articles),
        "translation_results": {},
    }

    save_json(results)

    failed_translations = []
    request_number = 0
    total_requests = len(articles) * len(MODELS)

    for article_index, article in enumerate(
        articles,
        start=1,
    ):
        original_title = article["title"].strip()

        article_result = {
            "input_title": original_title,
            "source": article.get("source", ""),
            "url": article.get("url", ""),
            "status": "success",
            "model_results": {},
        }

        print(f"\n{'=' * 72}")
        print(
            f"خبر {article_index}/{len(articles)}: "
            f"{original_title}"
        )

        for model_key, model_id in MODELS.items():
            request_number += 1

            if request_number > 1:
                time.sleep(SECONDS_BETWEEN_REQUESTS)

            print(
                f"\nمدل {model_key} "
                f"({request_number}/{total_requests}): {model_id}"
            )

            try:
                translation = translate_headline(
                    original_title,
                    model_id,
                )

                article_result["model_results"][model_key] = (
                    translation
                )

                print(
                    f"ترجمه: {translation['translated_title']}"
                )
                print(
                    f"زمان: {translation['elapsed_seconds']} ثانیه"
                )
                print(
                    f"توکن: {translation['total_tokens']}"
                )

            except Exception as error:
                error_result = {
                    "status": "error",
                    "model_requested": model_id,
                    "error": str(error),
                }

                article_result["model_results"][model_key] = (
                    error_result
                )
                article_result["status"] = "error"

                failed_translations.append({
                    "article": article_index,
                    "model": model_key,
                    "error": str(error),
                })

                print(f"خطا: {error}")

            # ترجمهٔ Nemotron در سطح اصلی خبر هم ذخیره می‌شود
            # تا اعتبارسنج فعلی workflow سازگار بماند.
            nemotron_result = article_result[
                "model_results"
            ].get("nemotron")

            if isinstance(nemotron_result, dict):
                if nemotron_result.get("status") == "success":
                    article_result["translated_title"] = (
                        nemotron_result["translated_title"]
                    )
                    article_result["total_tokens"] = (
                        nemotron_result["total_tokens"]
                    )
                    article_result["elapsed_seconds"] = (
                        nemotron_result["elapsed_seconds"]
                    )
                else:
                    article_result["translated_title"] = ""

            results["translation_results"][
                str(article_index)
            ] = article_result

            # ذخیرهٔ پیشرفت بعد از هر درخواست
            save_json(results)

        # موفقیت نهایی خبر مستلزم موفقیت هر سه مدل است.
        if any(
            article_result["model_results"].get(
                model_key, {}
            ).get("status") != "success"
            for model_key in MODELS
        ):
            article_result["status"] = "error"
        else:
            article_result["status"] = "success"

        results["translation_results"][
            str(article_index)
        ] = article_result

        save_json(results)

    results["test_metadata"]["finished_at"] = utc_now()

    results["test_metadata"]["successful_translation_count"] = (
        total_requests - len(failed_translations)
    )

    results["test_metadata"]["failed_translation_count"] = len(
        failed_translations
    )

    results["test_metadata"]["failed_translations"] = (
        failed_translations
    )

    save_json(results)

    print("\n" + "=" * 72)
    print("آزمایش تمام شد.")
    print(f"خبرها: {len(articles)}")
    print(f"مدل‌ها: {len(MODELS)}")

    print(
        f"ترجمه‌های موفق: "
        f"{total_requests - len(failed_translations)}"
        f"/{total_requests}"
    )

    print(f"فایل خروجی: {OUTPUT_FILE}")

    if failed_translations:
        raise RuntimeError(
            f"{len(failed_translations)} درخواست ترجمه ناموفق بود. "
            "جزئیات هر مدل در فایل خروجی ثبت شده است."
        )

    print("هر ۱۰ عنوان با هر سه مدل ترجمه شد.")


if __name__ == "__main__":
    main()
