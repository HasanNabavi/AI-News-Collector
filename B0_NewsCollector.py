import json
import feedparser
from datetime import datetime, timezone


def collect_news():
    with open("A_Source.json", "r", encoding="utf-8") as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    new_news = []

    for source in sources:
        feed = feedparser.parse(source["rss_url"])

        for item in feed.entries:
            title = item.get("title", "No title")
            link = item.get("link", "")
            published_at = item.get("published", "")

            news_item = {
                "title": title,
                "source": source["name"],
                "category": source["category"],
                "url": link,
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc).isoformat()
            }

            new_news.append(news_item)

    with open("B1_News.json", "w", encoding="utf-8") as file:
        json.dump(
            {"news": new_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Collected {len(new_news)} news items from RSS feeds.")
