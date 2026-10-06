import json
import html
import requests
from datetime import datetime, timezone


BOT_TOKEN = "8949593265:AAGalkZDAGolW3PG_MNiieNJBkRMJFrC_6o"
CHANNEL_ID = "@International_MetaTech"

INPUT_FILE = "H1_TelegramFormatedNews.json"
REPORT_FILE = "I1_TelegramPublishReport.json"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def prepare_telegram_text(article):

    formatted_text = article.get(
        "formatted_text",
        ""
    ).strip()

    link_text = article.get(
        "link_text",
        "🔗 Read the full story"
    ).strip()

    link_url = article.get(
        "link_url",
        ""
    ).strip()

    if not formatted_text:
        return None

    # Create a separate Telegram-safe copy.
    # H1 is never modified.
    text = html.escape(formatted_text)

    escaped_link_text = html.escape(link_text)

    if link_url and link_text in formatted_text:

        text = text.replace(
            escaped_link_text,
            f'<a href="{html.escape(link_url, quote=True)}">'
            f'{escaped_link_text}</a>',
            1
        )

    return text


def send_text(article, text):

    url = f"{TELEGRAM_API_URL}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": json.dumps({
            "is_disabled": True
        })
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=30
        )
    except requests.RequestException as error:
        return {
            "success": False,
            "error": f"Request error: {error}"
        }

    return parse_telegram_response(response)


def parse_telegram_response(response):

    try:
        result = response.json()

    except ValueError:

        return {
            "success": False,
            "error": (
                f"HTTP {response.status_code}: "
                f"Invalid JSON response"
            )
        }

    if response.status_code != 200:

        description = result.get(
            "description",
            response.text
        )

        return {
            "success": False,
            "error": (
                f"HTTP {response.status_code}: "
                f"{description}"
            )
        }

    if not result.get("ok"):

        return {
            "success": False,
            "error": result.get(
                "description",
                "Telegram API returned an unknown error."
            )
        }

    return {
        "success": True,
        "error": None
    }


def send_article(article):

    text = prepare_telegram_text(article)

    if not text:

        return {
            "success": False,
            "error": "Formatted text is empty.",
            "media_type": "none",
            "media_count": 0
        }

    # Media is intentionally disabled for now.
    # Only the formatted text is published.
    result = send_text(
        article,
        text
    )

    result["media_type"] = "none"
    result["media_count"] = 0

    return result


def main():

    execution_started_at = datetime.now(
        timezone.utc
    ).isoformat()

    print("Loading H1...")

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    news = data.get(
        "news",
        []
    )

    print(
        f"Total news: {len(news)}"
    )

    published = 0
    failed = 0
    skipped = 0

    video_count = 0
    photo_count = 0
    text_only_count = 0

    published_with_video = 0
    published_with_photo = 0
    published_text_only = 0

    failures = []

    for index, article in enumerate(
        news,
        start=1
    ):

        title = article.get(
            "title",
            "No title"
        )

        print()
        print(
            f"[{index}/{len(news)}]"
        )

        print(
            f"Title: {title}"
        )

        formatted_text = article.get(
            "formatted_text",
            ""
        ).strip()

        if not formatted_text:

            print(
                "Action: skipped - "
                "formatted text is empty."
            )

            skipped += 1

            failures.append({
                "title": title,
                "status": "skipped",
                "media_type": "none",
                "reason": "Formatted text is empty."
            })

            continue

        # Read media information only for reporting.
        # Media is NOT sent to Telegram.
        media_type = article.get(
            "media_type",
            "none"
        )

        media_urls = article.get(
            "media_urls",
            []
        )

        if not isinstance(media_urls, list):
            media_urls = []

        if media_type == "video":
            video_count += 1

        elif media_type == "photo":
            photo_count += 1

        else:
            text_only_count += 1

        print(
            f"Media in H1: {media_type}"
        )

        if media_urls:
            print(
                f"Media count in H1: "
                f"{len(media_urls)}"
            )

        print(
            "Action: publishing text only..."
        )

        result = send_article(article)

        if result.get("success"):

            print(
                "Result: published successfully."
            )

            published += 1
            published_text_only += 1

        else:

            error = result.get(
                "error",
                "Unknown error."
            )

            print(
                "Result: publishing failed."
            )

            print(
                f"Reason: {error}"
            )

            failed += 1

            failures.append({
                "title": title,
                "status": "failed",
                "media_type": "none",
                "media_count": 0,
                "reason": error
            })

    execution_finished_at = datetime.now(
        timezone.utc
    ).isoformat()

    report = {
        "execution": {
            "started_at": execution_started_at,
            "finished_at": execution_finished_at,
            "channel_id": CHANNEL_ID
        },

        "summary": {
            "total_articles_in_H1": len(news),
            "published_successfully": published,
            "failed": failed,
            "skipped": skipped,

            "articles_with_video_in_H1": video_count,
            "articles_with_photo_in_H1": photo_count,
            "text_only_articles_in_H1": text_only_count,

            "published_with_video": published_with_video,
            "published_with_photo": published_with_photo,
            "published_text_only": published_text_only
        },

        "failures": failures
    }

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 40)

    print(
        "I0 completed."
    )

    print(
        f"Published: {published}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Skipped: {skipped}"
    )

    print(
        f"Total news: {len(news)}"
    )

    print()

    print(
        f"News with video in H1: "
        f"{video_count}"
    )

    print(
        f"News with photo in H1: "
        f"{photo_count}"
    )

    print(
        f"Text only in H1: "
        f"{text_only_count}"
    )

    print()

    print(
        f"Published with video: "
        f"{published_with_video}"
    )

    print(
        f"Published with photo: "
        f"{published_with_photo}"
    )

    print(
        f"Published text only: "
        f"{published_text_only}"
    )

    print()

    print(
        f"I1 report: "
        f"{REPORT_FILE}"
    )


if __name__ == "__main__":
    main()
