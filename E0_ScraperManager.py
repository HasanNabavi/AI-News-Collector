import json
import importlib.util
from pathlib import Path


INPUT_FILE = "C1_NewsAfterLinkEquivalencyRun.json"
OUTPUT_FILE = "E1_NewsAfterScrapingRun.json"
SCRAPERS_DIR = Path("Scrapers")


def load_news():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    return data.get("news", [])


def load_scraper(source):
    scraper_filename = (
        source.replace(" ", "_") + ".py"
    )

    scraper_path = (
        SCRAPERS_DIR / scraper_filename
    )

    if not scraper_path.exists():
        return None, (
            f"Scraper file not found: "
            f"{scraper_path}"
        )

    module_name = (
        "scraper_"
        + source.replace(" ", "_")
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        scraper_path
    )

    if spec is None or spec.loader is None:
        return None, (
            f"Could not load scraper specification: "
            f"{scraper_path}"
        )

    try:
        module = (
            importlib.util.module_from_spec(spec)
        )

        spec.loader.exec_module(module)

    except Exception as error:
        return None, (
            f"Scraper import error: {error}"
        )

    if not hasattr(module, "scrape"):
        return None, (
            f"Scraper does not contain scrape(): "
            f"{scraper_path}"
        )

    return module, ""


def scrape_news_item(news_item):

    source = news_item.get(
        "source",
        ""
    )

    url = news_item.get(
        "url",
        ""
    )

    if not source:
        print(
            "Action: skip - source is empty."
        )
        return None

    if not url:
        print(
            "Action: skip - URL is empty."
        )
        return None

    scraper, error = load_scraper(
        source
    )

    if scraper is None:
        print(
            f"Action: error - {error}"
        )
        return None

    try:
        scraped_data = scraper.scrape(
            url
        )

    except Exception as error:
        print(
            "Action: error - "
            f"scraper execution failed: "
            f"{type(error).__name__}: {error}"
        )
        return None

    # ---------------------------------------------------------
    # None means that the scraper decided to skip this item.
    #
    # For example, BBC scraper returns None when the URL
    # is not an article.
    # ---------------------------------------------------------

    if scraped_data is None:
        print(
            "Action: skip - scraper rejected this page."
        )
        return None

    if not isinstance(
        scraped_data,
        dict
    ):
        print(
            "Action: error - scraper returned "
            "an invalid result."
        )
        return None

    result_item = news_item.copy()

    result_item["scraped_data"] = (
        scraped_data
    )

    return result_item


def scrape_manager():

    news = load_news()

    print(
        "AI & Robotics Scraper Manager"
    )
    print(
        "=" * 40
    )

    processed_news = []

    skipped_news = 0

    for index, news_item in enumerate(
        news,
        start=1
    ):

        title = news_item.get(
            "title",
            "No title"
        )

        source = news_item.get(
            "source",
            "Unknown source"
        )

        print()
        print(
            f"[{index}/{len(news)}] "
            f"{source}"
        )

        print(
            f"Title: {title}"
        )

        result_item = scrape_news_item(
            news_item
        )

        if result_item is None:
            skipped_news += 1
            continue

        processed_news.append(
            result_item
        )

        print(
            "Action: scraped successfully."
        )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "news": processed_news
            },
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        "=" * 40
    )

    print(
        f"Input news: {len(news)}"
    )

    print(
        f"Scraped news: "
        f"{len(processed_news)}"
    )

    print(
        f"Skipped news: "
        f"{skipped_news}"
    )

    print(
        "Scraper Manager completed."
    )


if __name__ == "__main__":
    scrape_manager()
