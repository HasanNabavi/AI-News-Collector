import json
import feedparser
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def normalize_url(url):
    parts = urlsplit(url)

    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid"
    }

    query_params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in tracking_params
    ]

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query_params),
        ""
    ))

    


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

    existing_urls = {
        normalize_url(item.get("url"))
        for item in existing_news
        if item.get("url")
    }
    new_news = []

    for source in sources:
        print()
        print(f"Source: {source['name']}")

        feed = feedparser.parse(source["rss_url"])

        print(f"News found: {len(feed.entries)}")

        for item in feed.entries:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            normalized_link = normalize_url(link)

            if normalized_link in existing_urls:
                continue

            existing_urls.add(normalized_link)
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
