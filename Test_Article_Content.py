import requests
import feedparser
from bs4 import BeautifulSoup


RSS_URL = "https://www.technologyreview.com/feed"


def get_first_article():
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        raise RuntimeError("No RSS entries found.")

    entry = feed.entries[0]

    return {
        "title": entry.get("title", ""),
        "url": entry.get("link", "")
    }


def download_page(url):
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
        timeout=20
    )

    response.raise_for_status()

    return response.text


def find_content_headings(soup):
    """
    Find headings that appear to belong to the main
    Gutenberg article content.
    """

    headings = []

    for heading in soup.find_all(
        ["h2", "h3", "h4"]
    ):

        if "wp-block-heading" not in (
            heading.get("class") or []
        ):
            continue

        text = heading.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        headings.append(
            heading
        )

    return headings


def extract_between_headings(
    heading,
    next_heading
):
    """
    Extract elements appearing after one content heading
    and before the next content heading.
    """

    elements = []

    current = heading.find_next()

    while current is not None:

        if current == next_heading:
            break

        if current.name in {
            "p",
            "img",
            "figure",
            "a"
        }:

            text = current.get_text(
                " ",
                strip=True
            )

            src = current.get(
                "src",
                ""
            )

            href = current.get(
                "href",
                ""
            )

            if text or src or href:
                elements.append({
                    "tag": current.name,
                    "text": text,
                    "src": src,
                    "href": href
                })

        current = current.find_next()

    return elements


def main():

    article = get_first_article()

    print(
        "RSS title:"
    )

    print(
        article["title"]
    )

    print()
    print(
        "URL:"
    )

    print(
        article["url"]
    )

    html = download_page(
        article["url"]
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    headings = find_content_headings(
        soup
    )

    print()
    print(
        "=" * 80
    )

    print(
        f"Content headings found: "
        f"{len(headings)}"
    )

    print(
        "=" * 80
    )

    for index, heading in enumerate(
        headings
    ):

        next_heading = None

        if index + 1 < len(headings):
            next_heading = headings[
                index + 1
            ]

        title = heading.get_text(
            " ",
            strip=True
        )

        print()
        print(
            "#" * 80
        )

        print(
            f"SECTION {index + 1}"
        )

        print(
            f"TITLE: {title}"
        )

        print(
            "#" * 80
        )

        elements = extract_between_headings(
            heading,
            next_heading
        )

        for element_index, element in enumerate(
            elements,
            start=1
        ):

            print()
            print(
                f"[{element_index}] "
                f"{element['tag']}"
            )

            if element["text"]:
                print(
                    f"TEXT: {element['text']}"
                )

            if element["src"]:
                print(
                    f"SRC: {element['src']}"
                )

            if element["href"]:
                print(
                    f"HREF: {element['href']}"
                )


if __name__ == "__main__":
    main()
