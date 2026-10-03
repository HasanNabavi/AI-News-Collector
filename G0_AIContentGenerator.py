import json

INPUT_FILE = "F1_NewsAfterAIGroupingRun.json"
OUTPUT_FILE = "G1_NewsAfterAIContentGenerationRun.json"


def main():
    print("Loading F1...")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    news = data.get("news", [])

    print(f"Total news: {len(news)}")

    first_article_of_group = {}

    for article in news:
        group_id = article.get("group_id")

        if group_id not in first_article_of_group:
            first_article_of_group[group_id] = article

    print(f"Total groups: {len(first_article_of_group)}")

    for group_id, first_article in first_article_of_group.items():

        generated_content = {
            "text": first_article.get("title", "")
        }

        for article in news:
            if article.get("group_id") == group_id:
                article["generated_content"] = generated_content

    output = {
        "news": news
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print()
    print("G0 completed.")
    print(f"Groups processed: {len(first_article_of_group)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
