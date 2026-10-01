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


def find_content_headings(soup):

    headings = []

    for heading in soup.find_all(
        ["h2", "h3", "h4"]
    ):

        if "wp-block-heading" not in (
            heading.get("class") or []
        ):
            continue

        text = heading.get_text(
            " ",
            strip=True
        )

        if text:
            headings.append(heading)

    return headings


def analyze_section(
    heading,
    next_heading
):

    paragraphs = []
    images = []
    links = []

    current = heading.find_next()

    while current is not None:

        if current == next_heading:
            break

        if current.name == "p":

            text = current.get_text(
                " ",
                strip=True
            )

            if len(text) >= 80:
                paragraphs.append(text)

        elif current.name == "img":

            src = current.get("src", "")

            if src:
                images.append(src)

        elif current.name == "a":

            href = current.get("href", "")

            if href:
                links.append(href)

        current = current.find_next()

    total_characters = sum(
        len(text)
        for text in paragraphs
    )

    return {
        "paragraphs": len(paragraphs),
        "characters": total_characters,
        "images": len(images),
        "links": len(links),
        "first_image": (
            images[0]
            if images
            else ""
        ),
        "first_link": (
            links[0]
            if links
            else ""
        )
    }


def main():

    article = get_first_article()

    print("RSS title:")
    print(article["title"])

    print()
    print("URL:")
    print(article["url"])

    html = download_page(
        article["url"]
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    headings = find_content_headings(
        soup
    )

    print()
    print("=" * 80)

    print(
        "Analyzing first 2 sections"
    )

    print("=" * 80)

    for index in range(
        min(2, len(headings))
    ):

        heading = headings[index]

        next_heading = None

        if index + 1 < len(headings):
            next_heading = headings[
                index + 1
            ]

        title = heading.get_text(
            " ",
            strip=True
        )

        result = analyze_section(
            heading,
            next_heading
        )

        print()
        print(
            f"SECTION {index + 1}"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"Paragraphs: "
            f"{result['paragraphs']}"
        )

        print(
            f"Characters: "
            f"{result['characters']}"
        )

        print(
            f"Images: "
            f"{result['images']}"
        )

        print(
            f"Links: "
            f"{result['links']}"
        )

        print(
            f"First image: "
            f"{result['first_image']}"
        )

        print(
            f"First link: "
            f"{result['first_link']}"
        )


if __name__ == "__main__":
    main()
