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


def get_article_page(url):

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
            f"HTTP status: {response.status_code}"
        )

        print(
            f"HTML length: {len(response.text)}"
        )

        return response.text

    except requests.RequestException as error:

        print(
            f"Request failed: {error}"
        )

        return None


def analyze_paragraph_ancestors(soup):

    paragraphs = []

    for paragraph in soup.find_all("p"):

        text = paragraph.get_text(
            " ",
            strip=True
        )

        if len(text) < 80:
            continue

        paragraphs.append(
            paragraph
        )

    print()
    print(
        f"Usable paragraphs found: {len(paragraphs)}"
    )

    if not paragraphs:
        return

    # --------------------------------------------------
    # Analyze first few long paragraphs
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("PARAGRAPH ANCESTOR ANALYSIS")
    print("=" * 70)

    sample_count = min(
        8,
        len(paragraphs)
    )

    for index in range(sample_count):

        paragraph = paragraphs[index
