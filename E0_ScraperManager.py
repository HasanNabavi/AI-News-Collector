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

    # ---------------------------------------------------------
    # Missing source or URL is an error.
    # A skipped item means that the scraper intentionally
    # decided not to process the page.
    # ---------------------------------------------------------

    if not source:
        print(
            "Action: error - source is empty."
        )
        return None, "error"

    if not url:
        print(
            "Action: error - URL is empty."
        )
        return None, "error"

    # ---------------------------------------------------------
    # Load the scraper associated with this news source.
    # ---------------------------------------------------------

    scraper, error = load_scraper(
        source
    )

    if scraper is None:
        print(
            f"Action: error - {error}"
        )
        return None, "error"

    # ---------------------------------------------------------
    # Scraper contract:
    #
    # dict  -> successful scraping
    # None  -> intentional skip
    # Exception -> scraping error
    # ---------------------------------------------------------

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
        return None, "error"

    # ---------------------------------------------------------
    # None means that the scraper intentionally skipped
    # this page.
    #
    # Example:
    # BBC scraper receives an iPlayer/video URL instead
    # of a /news/articles/ URL.
    # ---------------------------------------------------------

    if scraped_data is None:
        print(
            "Action: skip - scraper rejected this page."
        )
        return None, "skipped"

    # ---------------------------------------------------------
    # A scraper must return a dictionary when scraping
    # succeeds.
    # ---------------------------------------------------------

    if not isinstance(
        scraped_data,
        dict
    ):
        print(
            "Action: error - scraper returned "
            "an invalid result."
        )
        return None, "error"

    # ---------------------------------------------------------
    # Preserve the original RSS-level news data and add
    # the scraped data.
    # ---------------------------------------------------------

    result_item = news_item.copy()

    result_item["scraped_data"] = (
        scraped_data
    )

    return result_item, "success"


def scrape_manager():

    news = load_news()

    print(
        "AI & Robotics Scraper Manager"
    )

    print(
        "=" * 40
    )

    processed_news = []

    success_count = 0
    skipped_count = 0
    error_count = 0

    # ---------------------------------------------------------
    # Process every news item.
    # ---------------------------------------------------------

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

        result_item, result_status = (
            scrape_news_item(news_item)
        )

        # -----------------------------------------------------
        # Success
        # -----------------------------------------------------

        if result_status == "success":

            processed_news.append(
                result_item
            )

            success_count += 1

            print(
                "Action: scraped successfully."
            )

        # -----------------------------------------------------
        # Skipped
        # -----------------------------------------------------

        elif result_status == "skipped":

            skipped_count += 1

        # -----------------------------------------------------
        # Error
        # -----------------------------------------------------

        elif result_status == "error":

            error_count += 1

    # ---------------------------------------------------------
    # Create E1 output.
    # ---------------------------------------------------------

    output_data = {
        "scraping_summary": {
            "success": success_count,
            "skipped": skipped_count,
            "errors": error_count
        },
        "news": processed_news
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    # ---------------------------------------------------------
    # Final run summary
    # ---------------------------------------------------------

    print()
    print(
        "=" * 40
    )

    print(
        f"Input news: {len(news)}"
    )

    print(
        f"Success: {success_count}"
    )

    print(
        f"Skipped: {skipped_count}"
    )

    print(
        f"Errors: {error_count}"
    )

    print(
        f"Output news: {len(processed_news)}"
    )

    print(
        "Scraper Manager completed."
    )


if __name__ == "__main__":
    scrape_manager()
