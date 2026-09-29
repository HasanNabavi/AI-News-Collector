import json
import feedparser

# Load news sources
with open("sources.json", "r", encoding="utf-8") as file:
    sources_data = json.load(file)

sources = sources_data["sources"]

print("AI & Robotics News Collector")
print("=" * 40)

for source in sources:
    print()
    print(f"Source: {source['name']}")

    # Read RSS feed
    feed = feedparser.parse(source["rss_url"])

    print(f"News found: {len(feed.entries)}")

    # Show latest 5 news
    for item in feed.entries[:5]:
        title = item.get("title", "No title")
        link = item.get("link", "No link")

        print(f"- {title}")
        print(f"  {link}")
