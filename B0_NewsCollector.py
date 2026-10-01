import json
import feedparser
from datetime import datetime, timezone


def parse_entry_time(item):
    """
    Convert RSS publication/update time to UTC datetime.
    Prefer published time, then updated time.
    """

    time_struct = item.get("published_parsed")

    if time_struct is None:
        time_struct = item.get("updated_parsed")

    if time_struct is None:
        return None

    return datetime(*time_struct[:6], tzinfo=timezone.utc)


def load_last_successful_run():
    """
    Load the reference time of the last successful pipeline run.
    """

    with open("A1_RunState.json", "r", encoding="utf-8") as file:
        state_data = json.load(file)

    last_successful_run = state_data.get("last_successful_run", "")

    if not last_successful_run:
        return None

    return datetime.fromisoformat(
        last_successful_run.replace("Z", "+00:00")
    )


def collect_news():
    # Load news sources
    with open("A_Source.json", "r", encoding="utf-8") as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    # Load time reference
    last_successful_run = load_last_successful_run()

    print("AI & Robotics News Collector")
    print("=" * 40)

    if last_successful_run:
        print(f"Last successful run: {last_successful_run.isoformat()}")
    else:
        print("Last successful run: None (first run)")

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

            # Get parsed publication/update time
            entry_time = parse_entry_time(item)

            # Time Equivalency
            if last_successful_run is not None:

                # If the RSS item has no usable date,
                # skip it because we cannot safely determine
                # whether it is new.
                if entry_time is None:
                    continue

                # Skip news published before or at the last run
                if entry_time <= last_successful_run:
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
