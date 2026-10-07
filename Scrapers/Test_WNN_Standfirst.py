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


def load_wnn_news():
    input_path = Path(__file__).resolve().parent / INPUT_FILE

    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    news = data.get("news", [])

    wnn_news = [
        item for item in news
        if item.get("source") == "World Nuclear News"
    ]

    return wnn_news


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def normalize_text(text):
    return " ".join(text.split())


def find_standfirst_element(soup, meta_description):
    container = soup.find(id="internal_news_container")

    if not container:
        return None

    target = normalize_text(meta_description)

    if not target:
        return None

    for element in container.find_all(["p", "div", "span"]):
        text = normalize_text(
            element.get_text(" ", strip=True)
        )

        if text == target:
            return element

    return None


def print_element_info(label, element):
    if element is None:
        print(f"{label}: Not found")
        return

    print(f"{label}:")
    print(f"  Tag: {element.name}")
    print(f"  Class: {element.get('class')}")
    print(f"  ID: {element.get('id')}")
    print(
        f"  Text: "
        f"{normalize_text(element.get_text(' ', strip=True))[:500]}"
    )


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

    meta_description_tag = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    if meta_description_tag:
        meta_description = meta_description_tag.get(
            "content",
            ""
        ).strip()

        print(meta_description)
    else:
        meta_description = ""
        print("Not found")

    print("\n--- STANDFIRST ELEMENT ---")

    standfirst = find_standfirst_element(
        soup,
        meta_description
    )

    print_element_info(
        "Matched element",
        standfirst
    )

    if standfirst is not None:
        print("\n--- PARENT OF STANDFIRST ---")

        parent = standfirst.parent

        print_element_info(
            "Parent",
            parent
        )

        if parent is not None:
            print("\n--- GRANDPARENT OF STANDFIRST ---")

            grandparent = parent.parent

            print_element_info(
                "Grandparent",
                grandparent
            )


def main():
    news = load_wnn_news()

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
