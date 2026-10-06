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
            f'{escaped_link_text}'
            f'</a>',
            1
        )

    return text


def get_media(article):

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

    media_urls = [
        media_url.strip()
        for media_url in media_urls
        if isinstance(media_url, str)
        and media_url.strip()
    ]

    if media_type == "video" and media_urls:

        return "video", media_urls

    if media_type == "photo" and media_urls:

        return "photo", media_urls

    return "none", []


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


def send_photo(article, text, image_url):

    url = f"{TELEGRAM_API_URL}/sendPhoto"

    payload = {
        "chat_id": CHANNEL_ID,
        "photo": image_url,
        "caption": text,
        "parse_mode": "HTML"
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=60
        )

    except requests.RequestException as error:

        return {
            "success": False,
            "error": f"Request error: {error}"
        }

    return parse_telegram_response(response)


def send_video(article, text, video_url):

    url = f"{TELEGRAM_API_URL}/sendVideo"

    payload = {
        "chat_id": CHANNEL_ID,
        "video": video_url,
        "caption": text,
        "parse_mode": "HTML"
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=120
        )

    except requests.RequestException as error:

        return {
            "success": False,
            "error": f"Request error: {error}"
        }

    return parse_telegram_response(response)


def send_multiple_videos(article, text, video_urls):

    url = f"{TELEGRAM_API_URL}/sendMediaGroup"

    media = []

    for index, video_url in enumerate(video_urls):

        item = {
            "type": "video",
            "media": video_url
        }

        if index == 0:

            item["caption"] = text
            item["parse_mode"] = "HTML"

        media.append(item)

    payload = {
        "chat_id": CHANNEL_ID,
        "media": json.dumps(media)
    }

    try:

        response = requests.post(
            url,
            data=payload,
            timeout=180
        )

    except requests.RequestException as error:

        return {
            "success": False,
            "error": f"Request error: {error}"
        }

    return parse_telegram_response(response)


def send_article(article):

    text = prepare_telegram_text(article)

    if not text:

        return {
            "success": False,
            "error": "Formatted text is empty.",
            "media_type": "none",
            "media_count": 0
        }

    media_type, media_urls = get_media(article)

    if media_type == "video":

        if len(media_urls) == 1:

            result = send_video(
                article,
                text,
                media_urls[0]
            )

        else:

            result = send_multiple_videos(
                article,
                text,
                media_urls
            )

        result["media_type"] = "video"
        result["media_count"] = len(media_urls)

        return result

    if media_type == "photo":

        result = send_photo(
            article,
            text,
            media_urls[0]
        )

        result["media_type"] = "photo"
        result["media_count"] = 1

        return result

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

        media_type, media_urls = get_media(article)

        if media_type == "video":

            video_count += 1

        elif media_type == "photo":

            photo_count += 1

        else:

            text_only_count += 1

        print(
            f"Media: {media_type}"
        )

        if media_urls:

            print(
                f"Media count: {len(media_urls)}"
            )

        print(
            "Action: publishing..."
        )

        result = send_article(article)

        if result.get("success"):

            print(
                "Result: published successfully."
            )

            published += 1

            if media_type == "video":

                published_with_video += 1

            elif media_type == "photo":

                published_with_photo += 1

            else:

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
                "media_type": result.get(
                    "media_type",
                    media_type
                ),
                "media_count": result.get(
                    "media_count",
                    len(media_urls)
                ),
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
        f"News with video: {video_count}"
    )

    print(
        f"News with photo: {photo_count}"
    )

    print(
        f"Text only: {text_only_count}"
    )

    print()

    print(
        f"I1 report: {REPORT_FILE}"
    )


if __name__ == "__main__":
    main()
