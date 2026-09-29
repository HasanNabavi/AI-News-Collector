import json
import feedparser
from datetime import datetime, timezone


def collect_news():
    # Load news sources
    with open("sources.json", "r", encoding="utf-8") as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    # Load existing news
    try:
        with open("news.json", "r", encoding="utf-8") as file:
            news_data = json.load(file)
            existing_news = news_data.get("news", [])
    except FileNotFoundError:
        existing_news = []

    print("AI & Robotics News Collector")
    print("=" * 40)

    new_news = []

    for source in sources:
        print()
        print(f"Source: {source['name']}")

        feed = feedparser.parse(source["rss_url"])

        print(f"News found: {len(feed.entries)}")

        for item in feed.entries:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            published_at = item.get("published", "")

            print("Published:", published_at)

            news_item = {
                "title": title,
                "source": source["name"],
                "category": source["category"],
                "url": link,
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc).isoformat()
            }

            new_news.append(news_item)

    # Add new news to existing news
    all_news = existing_news + new_news

    # Save news
    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(
            {"news": all_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(f"Existing news: {len(existing_news)}")
    print(f"New news: {len(new_news)}")
    print(f"Total stored news: {len(all_news)}")


if __name__ == "__main__":
    collect_news()
