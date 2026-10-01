import json
import requests
from bs4 import BeautifulSoup


def test_article_content():

    with open(
        "B1_News.json",
        "r",
        encoding="utf-8"
    ) as file:
        news_data = json.load(file)

    news = news_data.get(
        "news",
        []
    )

    if not news:
        print("No news available in B1_News.json")
        return

    # Test only the first news item
    item = news[0]

    title = item.get(
        "title",
        ""
    )

    url = item.get(
        "url",
        ""
    )

    print("=" * 60)
    print("ARTICLE CONTENT TEST")
    print("=" * 60)

    print()
    print("Title:")
    print(title)

    print()
    print("URL:")
    print(url)

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

        print()
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
        print(
            "Request failed:"
        )

        print(error)

        return

    # --------------------------------------------------
    # Parse HTML
    # --------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    print()
    print("Page title:")

    if soup.title:
        print(
            soup.title.get_text(
                strip=True
            )
        )
    else:
        print("Not found")

    # --------------------------------------------------
    # Open Graph image
    # --------------------------------------------------

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    print()
    print("OG Image:")

    if og_image:
        print(
            og_image.get(
                "content",
                ""
            )
        )
    else:
        print("Not found")

    # --------------------------------------------------
    # Article tag
    # --------------------------------------------------

    article = soup.find(
        "article"
    )

    print()
    print("Article tag:")

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
            "First 1000 characters:"
        )

        print(
            article_text[:1000]
        )

    else:
        print(
            "Article tag not found"
        )

    print()
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    test_article_content()
