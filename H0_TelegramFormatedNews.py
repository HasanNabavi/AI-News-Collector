import json


INPUT_FILE = "G1_NewsAfterAIContentGenerationRun.json"
OUTPUT_FILE = "H1_TelegramFormatedNews.json"

CHANNEL_ID = "@International_MetaTech"


def get_hashtags(category):
    """
    Convert the article category into Telegram hashtags.
    """

    category = category.lower()

    hashtags = []

    if "robot" in category:
        hashtags.append("#robotics")

    if "ai" in category or "artificial intelligence" in category:
        hashtags.append("#ai")

    if "humanoid" in category:
        hashtags.append("#humanoid")

    if "quantum" in category:
        hashtags.append("#quantum")

    if "technology" in category and "#ai" not in hashtags:
        hashtags.append("#technology")

    if not hashtags:
        hashtags.append("#technology")

    return hashtags[:5]


def format_article(article):
    """
    Prepare one article for Telegram publishing.
    """

    generated_text = article.get(
        "generated_text",
        ""
    ).strip()

    url = article.get(
        "url",
        ""
    ).strip()

    category = article.get(
        "category",
        ""
    ).strip()

    source = article.get(
        "source",
        ""
    ).strip()

    published_at = article.get(
        "published_at",
        ""
    ).strip()

    scraped_data = article.get(
        "scraped_data",
        {}
    )

    main_image = scraped_data.get(
        "main_image",
        ""
    )

    videos = scraped_data.get(
        "videos",
        []
    )

    if not isinstance(videos, list):
        videos = []

    videos = [
        video.strip()
        for video in videos
        if isinstance(video, str) and video.strip()
    ]

    hashtags = get_hashtags(category)

    published_date = published_at[:10]

    formatted_text = (
        f"{generated_text}\n\n"
        f"🔗 Read the full story\n\n"
        f"{' '.join(hashtags)}\n"
        f"{source}\n"
        f"{published_date}\n"
        f"────────────\n"
        f"📢 {CHANNEL_ID}"
    )

    # Media priority:
    # 1. All videos
    # 2. Main image
    # 3. No media

    if videos:
        media_type = "video"
        media_urls = videos

    elif main_image:
        media_type = "photo"
        media_urls = [main_image]

    else:
        media_type = "none"
        media_urls = []

    return {
        "title": article.get("title", ""),
        "formatted_text": formatted_text,
        "link_text": "🔗 Read the full story",
        "link_url": url,
        "hashtags": hashtags,
        "source": source,
        "published_date": published_date,
        "channel_id": CHANNEL_ID,
        "media_type": media_type,
        "media_urls": media_urls
    }


def main():

    print("Loading G1...")

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

    formatted_news = []

    video_count = 0
    photo_count = 0
    text_only_count = 0

    for article in news:

        formatted_article = format_article(article)

        formatted_news.append(
            formatted_article
        )

        media_type = formatted_article["media_type"]

        if media_type == "video":
            video_count += 1

        elif media_type == "photo":
            photo_count += 1

        else:
            text_only_count += 1

    output = {
        "news": formatted_news
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("H0 completed.")
    print(
        f"Articles processed: "
        f"{len(formatted_news)}"
    )
    print(
        f"Articles with video: "
        f"{video_count}"
    )
    print(
        f"Articles with photo: "
        f"{photo_count}"
    )
    print(
        f"Text only: "
        f"{text_only_count}"
    )
    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
