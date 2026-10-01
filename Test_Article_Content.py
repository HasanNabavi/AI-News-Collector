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

        if text:
            headings.append(heading)

    return headings


def analyze_section(
    heading,
    next_heading
):

    paragraphs = []

    current = heading.find_next()

    while current is not None:

        if current == next_heading:
            break

        if current.name == "p":

            text = current.get_text(
                " ",
                strip=True
            )

            if len(text) >= 80:
                paragraphs.append(text)

        current = current.find_next()

    total_characters = sum(
        len(text)
        for text in paragraphs
    )

    return (
        len(paragraphs),
        total_characters
    )


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

        paragraph_count, character_count = (
            analyze_section(
                heading,
                next_heading
            )
        )

        print()
        print(
            f"SECTION {index + 1}"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"Paragraphs: {paragraph_count}"
        )

        print(
            f"Characters: {character_count}"
        )


if __name__ == "__main__":
    main()
