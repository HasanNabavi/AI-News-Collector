import json
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
    """
    Get the first article URL from the MIT Technology Review RSS feed.
    """

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
    """
    Download the article HTML.
    """

    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT
        },
        timeout=20
    )

    response.raise_for_status()

    return response.text


def analyze_page(html, rss_title):
    """
    Analyze the page structure and show
    possible article-content containers.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print()
    print(
        "Page analysis"
    )
    print(
        "=" * 60
    )

    print(
        f"RSS title:\n{rss_title}"
    )

    print()
    print(
        f"HTML length: {len(html)}"
    )

    print()

    candidates = []

    for tag in soup.find_all(
        ["article", "main", "section", "div"]
    ):

        paragraphs = []

        for paragraph in tag.find_all("p"):

            text = paragraph.get_text(
                " ",
                strip=True
            )

            if len(text) >= 80:
                paragraphs.append(
                    text
                )

        if not paragraphs:
            continue

        full_text = "\n".join(
            paragraphs
        )

        candidates.append({
            "tag": tag.name,
            "id": tag.get(
                "id",
                ""
            ),
            "class": " ".join(
                tag.get(
                    "class",
                    []
                )
            ),
            "paragraphs": len(
                paragraphs
            ),
            "text_length": len(
                full_text
            ),
            "text": full_text
        })

    candidates.sort(
        key=lambda x: (
            x["paragraphs"],
            x["text_length"]
        ),
        reverse=True
    )

    print(
        f"Candidates found: "
        f"{len(candidates)}"
    )

    print()

    for index, candidate in enumerate(
        candidates[:10],
        start=1
    ):

        print(
            f"Candidate #{index}"
        )

        print(
            "-" * 60
        )

        print(
            f"Tag: {candidate['tag']}"
        )

        print(
            f"ID: {candidate['id']}"
        )

        print(
            f"Class: {candidate['class']}"
        )

        print(
            f"Paragraphs: "
            f"{candidate['paragraphs']}"
        )

        print(
            f"Text length: "
            f"{candidate['text_length']}"
        )

        print()

        print(
            "FIRST 3 PARAGRAPHS:"
        )

        first_paragraphs = (
            candidate["text"]
            .split("\n")[:3]
        )

        for paragraph in first_paragraphs:
            print(
                f"- {paragraph}"
            )

        print()

        print(
            "LAST 3 PARAGRAPHS:"
        )

        last_paragraphs = (
            candidate["text"]
            .split("\n")[-3:]
        )

        for paragraph in last_paragraphs:
            print(
                f"- {paragraph}"
            )

        print()


def main():

    print(
        "MIT Technology Review "
        "Scraper Test"
    )

    print(
        "=" * 60
    )

    article = get_first_mit_article()

    print()
    print(
        "RSS Article"
    )

    print(
        "-" * 60
    )

    print(
        f"Title: {article['title']}"
    )

    print(
        f"URL: {article['url']}"
    )

    html = download_page(
        article["url"]
    )

    analyze_page(
        html,
        article["title"]
    )


if __name__ == "__main__":
    main()
