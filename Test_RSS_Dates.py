import json
import feedparser


def main():
    with open("A_Source.json", "r", encoding="utf-8") as file:
        sources_data = json.load(file)

    sources = sources_data["sources"]

    for source in sources:
        print()
        print("=" * 80)
        print(f"Source: {source['name']}")
        print(f"RSS: {source['rss_url']}")
        print("=" * 80)

        feed = feedparser.parse(source["rss_url"])

        if not feed.entries:
            print("No entries found.")
            continue

        # بررسی فقط اولین خبر هر منبع
        item = feed.entries[0]

        print(f"Title:")
        print(item.get("title", ""))

        print()
        print(f"published:")
        print(item.get("published", "NOT FOUND"))

        print()
        print(f"published_parsed:")
        print(item.get("published_parsed", "NOT FOUND"))

        print()
        print(f"updated:")
        print(item.get("updated", "NOT FOUND"))

        print()
        print(f"updated_parsed:")
        print(item.get("updated_parsed", "NOT FOUND"))

        print()


if __name__ == "__main__":
    main()
