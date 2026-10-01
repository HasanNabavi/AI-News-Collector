import requests
import feedparser
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)


def get_first_mit_article():
    rss_url = (
        "https://www.technologyreview.com/feed"
    )

    feed = feedparser.parse(
        rss_url
    )

    if not feed.entries:
        raise RuntimeError(
            "No RSS entries found."
        )

    item = feed.entries[0]

    return {
        "title": item.get(
            "title",
            ""
        ),
        "url": item.get(
            "link",
            ""
        )
    }


def download_page(url):
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=20
    )

    response.raise_for_status()

    return response.text


def get_usable_paragraphs(soup):
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

    return paragraphs


def analyze_paragraph(paragraph, index):

    text = paragraph.get_text(
        " ",
        strip=True
    )

    print()
    print(
        f"PARAGRAPH #{index}"
    )
    print(
        "=" * 60
    )

    print(
        f"Text:\n{text}"
    )

    print()

    print(
        "HTML tag:"
    )

    print(
        f"<{paragraph.name}>"
    )

    print()

    print(
        "Paragraph attributes:"
    )

    print(
        paragraph.attrs
    )

    print()

    print(
        "ANCESTOR STRUCTURE:"
    )

    current = paragraph

    level = 0

    while current is not None:

        if current.name is None:
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

        class_text = " ".join(
            classes
        )

        print(
            f"{level}. "
            f"{tag}"
            f"  id={element_id!r}"
            f"  class={class_text!r}"
        )

        current = current.parent

        level += 1

        if level >= 12:
            break


def analyze_page(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    paragraphs = get_usable_paragraphs(
        soup
    )

    print()
    print(
        "DOM STRUCTURE ANALYSIS"
    )
    print(
        "=" * 60
    )

    print(
        f"Usable paragraphs: "
        f"{len(paragraphs)}"
    )

    # Analyze the first 8 usable paragraphs.
    for index, paragraph in enumerate(
        paragraphs[:8],
        start=1
    ):

        analyze_paragraph(
            paragraph,
            index
        )


def main():

    print(
        "MIT Technology Review "
        "DOM Structure Test"
    )

    print(
        "=" * 60
    )

    article = get_first_mit_article()

    print()
    print(
        f"RSS title:\n{article['title']}"
    )

    print()
    print(
        f"URL:\n{article['url']}"
    )

    html = download_page(
        article["url"]
    )

    print()
    print(
        f"HTML length: {len(html)}"
    )

    analyze_page(
        html
    )


if __name__ == "__main__":
    main()
