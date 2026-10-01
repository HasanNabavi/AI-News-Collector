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

    return datetime(
        *time_struct[:6],
        tzinfo=timezone.utc
    )


def load_last_successful_run():
    """
    Load the timestamp of the most recent successful run.

    Supports both:
    - New A1 format with run history
    - Old A1 format during migration
    """

    with open(
        "A1_RunState.json",
        "r",
        encoding="utf-8"
    ) as file:
        state_data = json.load(file)

    # --------------------------------------------------
    # New A1 format
    # --------------------------------------------------
    #
    # {
    #   "runs": [
    #       {
    #           "run_number": 10,
    #           "timestamp_utc": "...",
    #           ...
    #       }
    #   ]
    # }
    #

    runs = state_data.get(
        "runs",
        []
    )

    if runs:
        latest_run = runs[0]

        timestamp_utc = latest_run.get(
            "timestamp_utc",
            ""
        )

        if timestamp_utc:
            return datetime.fromisoformat(
                timestamp_utc.replace(
                    "Z",
                    "+00:00"
                )
            )

    # --------------------------------------------------
    # Old A1 format
    # --------------------------------------------------
    #
    # {
    #   "last_successful_run": {
    #       "timestamp_utc": "...",
    #       ...
    #   }
    # }
    #

    last_successful_run = state_data.get(
        "last_successful_run",
        ""
    )

    if not last_successful_run:
        return None

    # Old format with dictionary
    if isinstance(
        last_successful_run,
        dict
    ):
        timestamp_utc = last_successful_run.get(
            "timestamp_utc",
            ""
        )

    # Very old format with direct string
    else:
        timestamp_utc = last_successful_run

    if not timestamp_utc:
        return None

    return datetime.fromisoformat(
        timestamp_utc.replace(
            "Z",
            "+00:00"
        )
    )


def collect_news():
    # --------------------------------------------------
    # Load news sources
    # --------------------------------------------------

    with open(
        "A_Source.json",
        "r",
        encoding="utf-8"
    ) as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    # --------------------------------------------------
    # Load time reference
    # --------------------------------------------------

    last_successful_run = (
        load_last_successful_run()
    )

    print(
        "AI & Robotics News Collector"
    )
    print(
        "=" * 40
    )

    if last_successful_run:
        print(
            "Last successful run: "
            f"{last_successful_run.isoformat()}"
        )
    else:
        print(
            "Last successful run: "
            "None (first run)"
        )

    new_news = []

    # --------------------------------------------------
    # Collect news from all sources
    # --------------------------------------------------

    for source in sources:

        print()
        print(
            f"Source: {source['name']}"
        )

        feed = feedparser.parse(
            source["rss_url"]
        )

        print(
            f"News found: "
            f"{len(feed.entries)}"
        )

        for item in feed.entries:

            title = item.get(
                "title",
                "No title"
            )

            link = item.get(
                "link",
                ""
            )

            published_at = item.get(
                "published",
                ""
            )

            # --------------------------------------------------
            # Parse RSS publication/update time
            # --------------------------------------------------

            entry_time = parse_entry_time(
                item
            )

            # --------------------------------------------------
            # Time Equivalency
            # --------------------------------------------------

            if last_successful_run is not None:

                # If the RSS item has no usable date,
                # skip it because we cannot safely determine
                # whether it is new.
                if entry_time is None:
                    continue

                # Skip news published before or at
                # the last successful run.
                if entry_time <= last_successful_run:
                    continue

            # --------------------------------------------------
            # Create news item
            # --------------------------------------------------

            news_item = {
                "title": title,
                "source": source["name"],
                "category": source["category"],
                "url": link,
                "published_at": published_at,
                "collected_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }

            new_news.append(
                news_item
            )

    # --------------------------------------------------
    # Save only news collected during this run
    # --------------------------------------------------

    with open(
        "B1_News.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "news": new_news
            },
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        f"New news: "
        f"{len(new_news)}"
    )


if __name__ == "__main__":
    collect_news()
