import json
import importlib.util
from pathlib import Path


INPUT_FILE = "D1_NewsAfterTittleEquivalencyRun.json"
OUTPUT_FILE = "E1_NewsAfterScrapingRun.json"
SCRAPERS_DIR = Path("Scrapers")


def load_news():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("news", [])


def load_scraper(source):
    scraper_filename = source.replace(" ", "_") + ".py"
    scraper_path = SCRAPERS_DIR / scraper_filename

    if not scraper_path.exists():
        return None, (
            f"Scraper file not found: {scraper_path}"
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
        module = importlib.util.module_from_spec(spec)
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
    source = news_item.get("source", "")
    url = news_item.get("url", "")

    result_item = news_item.copy()

    if not source:
        result_item["scraped_data"] = {
            "status": "error",
            "error": "News source is empty."
        }
        return result_item

    if not url:
        result_item["scraped_data"] = {
            "status": "error",
            "error": "News URL is empty."
        }
        return result_item

    scraper, error = load_scraper(source)

    if scraper is None:
        result_item["scraped_data"] = {
            "status": "error",
            "error": error
        }
        return result_item

    try:
        scraped_data = scraper.scrape(url)

        if not isinstance(scraped_data, dict):
            scraped_data = {
                "status": "error",
                "error": (
                    "Scraper returned an invalid result. "
                    "Expected a dictionary."
                )
            }

    except Exception as error:
        scraped_data = {
            "status": "error",
            "error": f"Scraper execution error: {error}"
        }

    result_item["scraped_data"] = scraped_data

    return result_item


def scrape_manager():
    news = load_news()

    print("AI & Robotics Scraper Manager")
    print("=" * 40)

    processed_news = []

    for index, news_item in enumerate(news, start=1):
        status = news_item.get(
            "title_similarity_status",
            ""
        )

        title = news_item.get(
            "title",
            "No title"
        )

        source = news_item.get(
            "source",
            "Unknown source"
        )

        print()
        print(f"[{index}/{len(news)}] {source}")
        print(f"Title: {title}")
        print(f"Similarity status: {status}")

        if status == "Duplicate":
            print("Action: skipped (Duplicate)")
            continue

        if status not in {"New", "Suspicious"}:
            print("Action: skipped (unknown status)")
            continue

        print("Action: scraping...")

        result_item = scrape_news_item(news_item)

        scraped_status = result_item.get(
            "scraped_data",
            {}
        ).get(
            "status",
            "unknown"
        )

        print(f"Scraper status: {scraped_status}")

        if scraped_status == "error":
            error_message = result_item[
                "scraped_data"
            ].get(
                "error",
                "Unknown scraper error."
            )

            print(f"Error: {error_message}")

        processed_news.append(result_item)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {"news": processed_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 40)
    print(f"Input news: {len(news)}")
    print(f"Output news: {len(processed_news)}")
    print(
        f"Skipped duplicates: "
        f"{sum(1 for item in news if item.get('title_similarity_status') == 'Duplicate')}"
    )
    print("Scraper Manager completed.")


if __name__ == "__main__":
    scrape_manager()
