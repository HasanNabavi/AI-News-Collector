import json

from goose3 import Goose


INPUT_FILE = "C1_NewsAfterLinkEquivalencyRun.json"
OUTPUT_FILE = "A1_Test_MediaExtractor.json"


def extract_main_image(goose, url):
    try:
        article = goose.extract(url=url)

        if article.top_image:
            return article.top_image.src or ""

    except Exception:
        pass

    return ""


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    news = data["news"]

    goose = Goose({
        "browser_user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    })

    results = []

    for item in news:

        title = item.get(
            "title",
            ""
        )

        article_url = item.get(
            "url",
            ""
        )

        image_url = extract_main_image(
            goose,
            article_url
        )

        results.append({
            "title": title,
            "article_url": article_url,
            "image_url": image_url
        })

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    main()
