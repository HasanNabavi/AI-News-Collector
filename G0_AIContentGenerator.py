import json

INPUT_FILE = "F1_NewsAfterAIGroupingRun.json"
OUTPUT_FILE = "G1_NewsAfterAIContentGenerationRun.json"


def main():
    print("Loading F1...")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    news = data.get("news", [])

    print(f"Total news: {len(news)}")

    generated_content = {}

    for article in news:
        group_id = article.get("group_id")

        if group_id not in generated_content:
            generated_content[group_id] = {
                "text": article.get("title", ""),
                "images": [],
                "videos": []
            }

    print(f"Total groups: {len(generated_content)}")

    output = {
        "news": news,
        "generated_content": generated_content
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print()
    print("G0 completed.")
    print(f"Groups processed: {len(generated_content)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
