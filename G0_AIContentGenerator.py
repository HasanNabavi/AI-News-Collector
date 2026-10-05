import json


INPUT_FILE = "F1_NewsAfterAIGroupingRun.json"
OUTPUT_FILE = "G1_NewsAfterAIContentGenerationRun.json"


def get_first_50_words(text):
    """
    Return the first 50 words of the given text.
    If the text contains fewer than 50 words,
    return the entire text.
    """

    words = text.split()

    return " ".join(words[:50])


def main():

    print("Loading F1...")

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    news = data.get(
        "news",
        []
    )

    print(
        f"Total news: {len(news)}"
    )

    for article in news:

        scraped_data = article.get(
            "scraped_data",
            {}
        )

        full_text = scraped_data.get(
            "text",
            ""
        )

        article["generated_text"] = (
            get_first_50_words(full_text)
        )

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
    print("G0 completed.")
    print(
        f"Articles processed: "
        f"{len(news)}"
    )
    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
