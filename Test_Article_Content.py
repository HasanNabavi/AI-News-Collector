import requests
from bs4 import BeautifulSoup


ARTICLE_URL = (
    "https://www.technologyreview.com/2026/10/01/"
    "1145588/ai-mind-reading-reconstructs-"
    "what-youre-looking-at/"
)


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


def main():

    print("Article URL:")
    print(ARTICLE_URL)

    html = download_page(
        ARTICLE_URL
    )

    print()
    print(
        f"HTML length: {len(html)}"
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print()
    print("=" * 80)
    print("HEADINGS")
    print("=" * 80)

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4"]
    )

    for index, heading in enumerate(
        headings,
        start=1
    ):

        text = heading.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        print()
        print(
            f"Heading #{index}"
        )

        print(
            f"Tag: {heading.name}"
        )

        print(
            f"Text: {text}"
        )

        print(
            f"Class: "
            f"{heading.get('class', [])}"
        )

    print()
    print("=" * 80)
    print("ARTICLE STRUCTURE")
    print("=" * 80)

    paragraphs = soup.find_all("p")

    usable_paragraphs = []

    for paragraph in paragraphs:

        text = paragraph.get_text(
            " ",
            strip=True
        )

        if len(text) >= 80:
            usable_paragraphs.append(
                text
            )

    print()
    print(
        f"Total usable paragraphs: "
        f"{len(usable_paragraphs)}"
    )

    total_characters = sum(
        len(text)
        for text in usable_paragraphs
    )

    print(
        f"Total characters: "
        f"{total_characters}"
    )

    print()
    print("=" * 80)
    print("FIRST 5 PARAGRAPHS")
    print("=" * 80)

    for index, text in enumerate(
        usable_paragraphs[:5],
        start=1
    ):

        print()
        print(
            f"Paragraph {index}:"
        )

        print(
            text[:500]
        )


if __name__ == "__main__":
    main()
