import feedparser
import requests
from bs4 import BeautifulSoup


RSS_URL = (
    "https://www.technologyreview.com/feed/"
)


def test_article_content():

    print("=" * 60)
    print("ARTICLE CONTENT TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Read RSS
    # --------------------------------------------------

    print()
    print("Reading RSS...")

    feed = feedparser.parse(
        RSS_URL
    )

    print(
        f"RSS entries found: "
        f"{len(feed.entries)}"
    )

    if not feed.entries:
        print(
            "No RSS entries found."
        )
        return

    # --------------------------------------------------
    # Select first RSS item
    # --------------------------------------------------

    item = feed.entries[0]

    title = item.get(
        "title",
        ""
    )

    url = item.get(
        "link",
        ""
    )

    print()
    print("Selected article:")
    print(title)

    print()
    print("URL:")
    print(url)

    if not url:
        print(
            "Article URL not found."
        )
        return

    # --------------------------------------------------
    # Request article page
    # --------------------------------------------------

    print()
    print("Requesting article page...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print(
            f"HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"Content length: "
            f"{len(response.text)}"
        )

    except requests.RequestException as error:

        print()
        print("Request failed:")
        print(error)

        return

    # --------------------------------------------------
    # Parse HTML
    # --------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # --------------------------------------------------
    # HTML title
    # --------------------------------------------------

    print()
    print("Page title:")

    if soup.title:

        print(
            soup.title.get_text(
                strip=True
            )
        )

    else:

        print(
            "Not found"
        )

    # --------------------------------------------------
    # Open Graph image
    # --------------------------------------------------

    print()
    print("OG Image:")

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:

        print(
            og_image.get(
                "content",
                ""
            )
        )

    else:

        print(
            "Not found"
        )

    # --------------------------------------------------
    # Article tag
    # --------------------------------------------------

    print()
    print("Article tag:")

    article = soup.find(
        "article"
    )

    if article:

        article_text = article.get_text(
            " ",
            strip=True
        )

        print(
            f"Text length: "
            f"{len(article_text)}"
        )

        print()
        print(
            "First 1500 characters:"
        )

        print(
            article_text[:1500]
        )

    else:

        print(
            "Article tag not found"
        )

    # --------------------------------------------------
    # Video detection
    # --------------------------------------------------

    print()
    print("Video elements:")

    videos = soup.find_all(
        "video"
    )

    print(
        f"Video tags found: "
        f"{len(videos)}"
    )

    # --------------------------------------------------
    # Iframe detection
    # --------------------------------------------------

    print()
    print("Iframe elements:")

    iframes = soup.find_all(
        "iframe"
    )

    print(
        f"Iframes found: "
        f"{len(iframes)}"
    )

    # --------------------------------------------------
    # Test completed
    # --------------------------------------------------

    print()
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    test_article_content()
