import requests
import feedparser
from bs4 import BeautifulSoup


RSS_URL = (
    "https://www.technologyreview.com/feed"
)

NUMBER_OF_ARTICLES = 5


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


def analyze_article(title, url):

    print()
    print("=" * 80)
    print("ARTICLE")
    print("=" * 80)

    print()
    print("Title:")
    print(title)

    print()
    print("URL:")
    print(url)

    try:
        html = download_page(url)

    except Exception as error:
        print()
        print(
            f"DOWNLOAD ERROR: {error}"
        )
        return

    print()
    print(
        f"HTML length: {len(html)}"
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    container = soup.find(
        id="content--body"
    )

    print()
    print(
        f"#content--body: "
        f"{'FOUND' if container else 'NOT FOUND'}"
    )

    if container is None:
        return

    paragraphs = []

    for p in container.find_all("p"):

        text = p.get_text(
            " ",
            strip=True
        )

        if len(text) >= 80:
            paragraphs.append(
                text
            )

    images = container.find_all(
        "img"
    )

    links = container.find_all(
        "a",
        href=True
    )

    print()
    print(
        f"Usable paragraphs: "
        f"{len(paragraphs)}"
    )

    print(
        f"Characters: "
        f"{sum(len(t) for t in paragraphs)}"
    )

    print(
        f"Images: "
        f"{len(images)}"
    )

    print(
        f"Links: "
        f"{len(links)}"
    )

    print()
    print("-" * 80)
    print("FIRST 2 PARAGRAPHS")
    print("-" * 80)

    for i, text in enumerate(
        paragraphs[:2],
        1
    ):

        print()
        print(
            f"Paragraph {i}:"
        )

        print(
            text[:500]
        )

    print()
    print("-" * 80)
    print("LAST 2 PARAGRAPHS")
    print("-" * 80)

    last_paragraphs = paragraphs[-2:]

    for i, text in enumerate(
        last_paragraphs,
        1
    ):

        print()
        print(
            f"Paragraph {i}:"
        )

        print(
            text[:500]
        )


def main():

    print(
        "MIT Technology Review RSS Test"
    )

    print(
        "=" * 80
    )

    print()
    print("RSS URL:")
    print(RSS_URL)

    print()
    print(
        f"Testing first "
        f"{NUMBER_OF_ARTICLES} RSS items..."
    )

    feed = feedparser.parse(
        RSS_URL
    )

    print()
    print(
        f"RSS items found: "
        f"{len(feed.entries)}"
    )

    articles = feed.entries[
        :NUMBER_OF_ARTICLES
    ]

    for index, item in enumerate(
        articles,
        1
    ):

        title = item.get(
            "title",
            "No title"
        )

        url = item.get(
            "link",
            ""
        )

        print()
        print(
            f"\n######## ARTICLE "
            f"{index} / "
            f"{len(articles)} ########"
        )

        if not url:
            print(
                "URL NOT FOUND"
            )
            continue

        analyze_article(
            title,
            url
        )


if __name__ == "__main__":
    main()
