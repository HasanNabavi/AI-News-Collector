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


def print_heading_structure(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    print()
    print("=" * 80)
    print("HEADINGS")
    print("=" * 80)

    print(
        f"Total headings found: {len(headings)}"
    )

    for index, heading in enumerate(
        headings,
        start=1
    ):

        text = heading.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        print()
        print(
            f"Heading #{index}"
        )

        print(
            f"Tag: {heading.name}"
        )

        print(
            f"Text: {text}"
        )

        print(
            f"ID: {heading.get('id', '')}"
        )

        print(
            f"Class: {heading.get('class', [])}"
        )

        print(
            "Parent chain:"
        )

        current = heading

        for level in range(8):

            if current is None:
                break

            tag = current.name

            element_id = current.get(
                "id",
                ""
            )

            classes = current.get(
                "class",
                []
            )

            print(
                f"  {level}: "
                f"{tag} "
                f"id={element_id} "
                f"class={classes}"
            )

            current = current.parent


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

    print()
    print(
        f"HTML length: {len(html)}"
    )

    print_heading_structure(
        html
    )


if __name__ == "__main__":
    main()
