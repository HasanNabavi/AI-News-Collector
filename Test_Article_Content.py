import json
import feedparser
import requests
from bs4 import BeautifulSoup


TEST_SOURCES = [
    {
        "name": "MIT Technology Review",
        "rss_url": "https://www.technologyreview.com/feed/"
    },
    {
        "name": "TechCrunch",
        "rss_url": "https://techcrunch.com/feed/"
    },
    {
        "name": "BBC Technology",
        "rss_url": "https://feeds.bbci.co.uk/news/technology/rss.xml"
    }
]


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


def extract_html_paragraphs(soup):

    selectors = [
        '[itemprop="articleBody"]',
        '[class*="article-body"]',
        '[class*="articleBody"]',
        '[class*="story-body"]',
        '[class*="storyBody"]',
        '[class*="article-content"]',
        '[class*="articleContent"]',
        '[class*="story-content"]',
        '[class*="storyContent"]',
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

                return (
                    combined_text,
                    selector
                )

    return None, None


def extract_images(soup):

    images = []

    # OG image

    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image:

        image_url = og_image.get(
            "content",
            ""
        )

        if image_url:
            images.append(image_url)

    # Standard images

    for image in soup.find_all(
        "img"
    ):

        src = (
            image.get("src")
            or image.get("data-src")
            or ""
        )

        if src and src not in images:
            images.append(src)

    return images


def test_source(source):

    print()
    print("=" * 70)
    print(
        f"SOURCE: {source['name']}"
    )
    print("=" * 70)

    # --------------------------------------------------
    # RSS
    # --------------------------------------------------

    print()
    print("Reading RSS...")

    feed = feedparser.parse(
        source["rss_url"]
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
    # Select first article
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
    # Request page
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

        print("Not found")

    # --------------------------------------------------
    # Image
    # --------------------------------------------------

    print()
    print("Images:")

    images = extract_images(
        soup
    )

    print(
        f"Images found: "
        f"{len(images)}"
    )

    if images:

        print(
            "First image:"
        )

        print(
            images[0]
        )

    # --------------------------------------------------
    # JSON-LD
    # --------------------------------------------------

    print()
    print(
        "Method 1: JSON-LD articleBody"
    )

    json_ld_text = (
        extract_json_ld_article_body(
            soup
        )
    )

    if json_ld_text:

        print("SUCCESS")

        print(
            f"Text length: "
            f"{len(json_ld_text)}"
        )

        print()
        print(
            "First 500 characters:"
        )

        print(
            json_ld_text[:500]
        )

    else:

        print(
            "No usable articleBody found."
        )

    # --------------------------------------------------
    # HTML paragraphs
    # --------------------------------------------------

    print()
    print(
        "Method 2: HTML paragraph extraction"
    )

    paragraph_text, selector = (
        extract_html_paragraphs(
            soup
        )
    )

    if paragraph_text:

        print("SUCCESS")

        print(
            f"Selector: "
            f"{selector}"
        )

        print(
            f"Text length: "
            f"{len(paragraph_text)}"
        )

        print()
        print(
            "First 500 characters:"
        )

        print(
            paragraph_text[:500]
        )

        print()
        print(
            "Last 1000 characters:"
        )

        print(
            paragraph_text[-1000:]
        )

    else:

        print(
            "No usable article text found."
        )

    # --------------------------------------------------
    # Video
    # --------------------------------------------------

    print()
    print("Video:")

    videos = soup.find_all(
        "video"
    )

    print(
        f"Video tags found: "
        f"{len(videos)}"
    )

    # --------------------------------------------------
    # Iframe
    # --------------------------------------------------

    print()
    print("Iframe:")

    iframes = soup.find_all(
        "iframe"
    )

    print(
        f"Iframes found: "
        f"{len(iframes)}"
    )


def main():

    print()
    print("=" * 70)
    print("MULTI-SOURCE ARTICLE CONTENT TEST")
    print("=" * 70)

    for source in TEST_SOURCES:

        test_source(
            source
        )

    print()
    print("=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
