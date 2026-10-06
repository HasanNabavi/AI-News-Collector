import json
import html
import requests


BOT_TOKEN = "<KEEP_YOUR_EXISTING_BOT_TOKEN_HERE>"
CHANNEL_ID = "@International_MetaTech"

INPUT_FILE = "H1_TelegramFormatedNews.json"

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


def send_message(article):

    text = prepare_telegram_text(article)

    if not text:
        return False

    url = f"{TELEGRAM_API_URL}/sendMessage"

    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    response = requests.post(
        url,
        data=payload,
        timeout=30
    )

    if response.status_code != 200:

        print("Telegram API error:")
        print(response.text)

        return False

    result = response.json()

    if not result.get("ok"):

        print("Telegram API returned an error:")
        print(result)

        return False

    return True


def main():

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
    skipped = 0

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
            continue

        print(
            "Action: publishing text..."
        )

        if send_message(article):

            print(
                "Result: published successfully."
            )

            published += 1

        else:

            print(
                "Result: publishing failed."
            )

    print()
    print("=" * 40)
    print("I0 completed.")
    print(
        f"Published: {published}"
    )
    print(
        f"Skipped: {skipped}"
    )
    print(
        f"Total news: {len(news)}"
    )


if __name__ == "__main__":
    main()
