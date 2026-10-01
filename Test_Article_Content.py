import json
import feedparser
import requests
from bs4 import BeautifulSoup


RSS_URL = (
    "https://www.technologyreview.com/feed/"
)


def extract_json_ld_article_body(soup):

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        try:
            data = json.loads(
                script.string or script.get_text()
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):
            continue

        objects = []

        if isinstance(data, dict):
            objects.append(data)

            graph = data.get(
                "@graph",
                []
            )

            if isinstance(graph, list):
                objects.extend(graph)

        elif isinstance(data, list):
            objects.extend(data)

        for obj in objects:

            if not isinstance(obj, dict):
                continue

            article_body = obj.get(
                "articleBody"
            )

            if (
                isinstance(article_body, str)
                and len(article_body.strip()) > 300
            ):
                return article_body.strip()

    return None


def extract_paragraphs(soup):

    selectors = [
        '[itemprop="articleBody"]',
        '[class*="article-body"]',
        '[class*="story-body"]',
        "article",
        "main"
    ]

    for selector in selectors:

        containers = soup.select(
            selector
        )

        for container in containers:

            paragraphs = container.find_all(
                "p"
            )

            texts = []

            for paragraph in paragraphs:

                text = paragraph.get_text(
                    " ",
                    strip=True
                )

                if len(text) >= 40:
                    texts.append(text)

            combined_text = "\n\n".join(
                texts
            )

            if len(combined_text) >= 300:
                return combined_text

    return None


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
    # Page title
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
    # OG Image
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
    # Method 1: JSON-LD articleBody
    # --------------------------------------------------

    print()
    print("Method 1: JSON-LD articleBody")

    json_ld_text = extract_json_ld_article_body(
        soup
    )

    if json_ld_text:

        print(
            "SUCCESS"
        )

        print(
            f"Text length: "
            f"{len(json_ld_text)}"
        )

        print()
        print(
            "First 1500 characters:"
        )

        print(
            json_ld_text[:1500]
        )

    else:

        print(
            "No usable articleBody found."
        )

    # --------------------------------------------------
    # Method 2: HTML paragraphs
    # --------------------------------------------------

    print()
    print("Method 2: HTML paragraph extraction")

    paragraph_text = extract_paragraphs(
        soup
    )

    if paragraph_text:

        print(
            "SUCCESS"
        )

        print(
            f"Text length: "
            f"{len(paragraph_text)}"
        )

        print()
        print(
            "First 1500 characters:"
        )

        print(
            paragraph_text[:1500]
        )

    else:

        print(
            "No usable article text found."
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
