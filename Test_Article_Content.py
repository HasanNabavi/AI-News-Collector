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


def analyze_page(title, url):

    print()
    print("=" * 80)
    print("PAGE")
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

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    container = soup.find(
        id="content--body"
    )

    if container is None:

        print()
        print(
            "#content--body NOT FOUND"
        )

        return

    print()
    print(
        "#content--body FOUND"
    )

    # --------------------------------------------------
    # Headings
    # --------------------------------------------------

    headings = container.find_all(
        ["h1", "h2", "h3", "h4"]
    )

    print()
    print(
        f"Headings found: "
        f"{len(headings)}"
    )

    print()
    print("-" * 80)
    print("HEADINGS")
    print("-" * 80)

    for index, heading in enumerate(
        headings,
        1
    ):

        text = heading.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        print(
            f"{index}. "
            f"{heading.name}: "
            f"{text[:250]}"
        )

    # --------------------------------------------------
    # Newsletter indicators
    # --------------------------------------------------

    full_text = container.get_text(
        " ",
        strip=True
    )

    newsletter_phrases = [
        "This is today's edition of The Download",
        "our weekday newsletter",
        "This article is from The Spark",
        "weekly climate newsletter",
        "newsletter"
    ]

    print()
    print("-" * 80)
    print("NEWSLETTER INDICATORS")
    print("-" * 80)

    for phrase in newsletter_phrases:

        found = phrase.lower() in full_text.lower()

        print(
            f"{phrase}: "
            f"{'FOUND' if found else 'NOT FOUND'}"
        )


def main():

    print(
        "MIT Technology Review"
    )

    print(
        "Page Type Detection Test"
    )

    print(
        "=" * 80
    )

    print()
    print(
        f"Reading first "
        f"{NUMBER_OF_ARTICLES} RSS items..."
    )

    feed = feedparser.parse(
        RSS_URL
    )

    articles = feed.entries[
        :NUMBER_OF_ARTICLES
    ]

    print()
    print(
        f"RSS items found: "
        f"{len(feed.entries)}"
    )

    for index, item in enumerate(
        articles,
        1
    ):

        print()
        print(
            f"\n######## "
            f"{index} / "
            f"{len(articles)} "
            f"########"
        )

        title = item.get(
            "title",
            "No title"
        )

        url = item.get(
            "link",
            ""
        )

        if not url:

            print(
                "URL NOT FOUND"
            )

            continue

        analyze_page(
            title,
            url
        )


if __name__ == "__main__":
    main()
