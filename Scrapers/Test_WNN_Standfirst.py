import json
import requests

from bs4 import BeautifulSoup
from pathlib import Path


INPUT_FILE = "../C1_NewsAfterLinkEquivalencyRun.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def load_first_10_wnn_news():
    input_path = Path(__file__).resolve().parent / INPUT_FILE

    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    news = data.get("news", [])

    wnn_news = [
        item for item in news
        if item.get("source") == "World Nuclear News"
    ]

    return wnn_news[:10]


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def inspect_first_text_elements(soup):
    print("\nFirst text-containing elements:")

    count = 0

    for element in soup.find_all(["p", "div", "span"]):
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if len(text) < 40:
            continue

        count += 1

        print(f"\n  Element #{count}")
        print(f"  Tag: {element.name}")
        print(f"  Class: {element.get('class')}")
        print(f"  ID: {element.get('id')}")
        print(f"  Text: {text[:300]}")

        if count >= 8:
            break


def inspect_article(url, index):
    print("\n" + "=" * 80)
    print(f"ARTICLE {index}")
    print("=" * 80)
    print(f"URL: {url}")

    try:
        html = get_html(url)
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}")
        return

    soup = BeautifulSoup(html, "html.parser")

    print(f"HTML length: {len(html):,} characters")

    print("\n--- TITLE ---")

    title = soup.find("title")

    if title:
        print(title.get_text(" ", strip=True))
    else:
        print("Not found")

    print("\n--- META DESCRIPTION ---")

    meta_description = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta_description:
        print(meta_description.get("content", "").strip())
    else:
        print("Not found")

    print("\n--- FIRST TEXT ELEMENTS ---")

    inspect_first_text_elements(soup)


def main():
    news = load_first_10_wnn_news()

    print("World Nuclear News - Standfirst HTML Test")
    print("=" * 80)
    print(f"Found WNN articles: {len(news)}")

    if not news:
        print("No World Nuclear News articles found.")
        return

    for index, news_item in enumerate(news, start=1):
        url = news_item.get("url", "")

        if not url:
            print(f"\nARTICLE {index}: URL is empty.")
            continue

        inspect_article(url, index)

    print("\n" + "=" * 80)
    print("Test completed.")


if __name__ == "__main__":
    main()
