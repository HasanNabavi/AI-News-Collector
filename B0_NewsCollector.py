import json
import feedparser
from datetime import datetime, timezone


def collect_news():
    # Load news sources
    with open("A_Source.json", "r", encoding="utf-8") as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    # Load previously collected news
    with open("B2_LastCollectedNews.json", "r", encoding="utf-8") as file:
        last_news_data = json.load(file)

    last_news = last_news_data.get("news", [])

    # Create a set of previously collected URLs
    previous_urls = {
        item.get("url", "")
        for item in last_news
        if item.get("url", "")
    }

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
            link = item.get("link", "")
            published_at = item.get("published", "")

            # Skip news already collected in the previous run
            if link in previous_urls:
                continue

            news_item = {
                "title": title,
                "source": source["name"],
                "category": source["category"],
                "url": link,
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc).isoformat()
            }

            new_news.append(news_item)

    # Save only newly collected news
    with open("B1_News.json", "w", encoding="utf-8") as file:
        json.dump(
            {"news": new_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(f"New news: {len(new_news)}")


if __name__ == "__main__":
    collect_news()
