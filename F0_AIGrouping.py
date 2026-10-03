import json


INPUT_FILE = "E1_NewsAfterScrapingRun.json"
OUTPUT_FILE = "F1_NewsAfterAIGroupingRun.json"


def main():

    print("Loading E1...")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    news = data.get("news", [])

    print(f"Total news: {len(news)}")

    # Temporary grouping:
    # Every article gets its own unique group.

    for index, article in enumerate(news, start=1):

        article["group_id"] = f"G{index:04d}"

    output = {
        "news": news
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
    print("F0 completed.")
    print(f"Groups created: {len(news)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
