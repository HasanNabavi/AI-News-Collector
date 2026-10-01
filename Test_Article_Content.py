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

    container = soup.find(
        id="content--body"
    )

    print()
    print("=" * 80)
    print("CONTENT BODY")
    print("=" * 80)

    if container is None:
        print(
            "content--body NOT FOUND"
        )
        return

    paragraphs = []

    for p in container.find_all("p"):

        text = p.get_text(
            " ",
            strip=True
        )

        if len(text) >= 80:
            paragraphs.append(
                text
            )

    images = container.find_all(
        "img"
    )

    links = container.find_all(
        "a",
        href=True
    )

    print(
        f"Usable paragraphs: "
        f"{len(paragraphs)}"
    )

    print(
        f"Characters: "
        f"{sum(len(t) for t in paragraphs)}"
    )

    print(
        f"Images: "
        f"{len(images)}"
    )

    print(
        f"Links: "
        f"{len(links)}"
    )

    print()
    print("=" * 80)
    print("FIRST 5 PARAGRAPHS")
    print("=" * 80)

    for i, text in enumerate(
        paragraphs[:5],
        1
    ):

        print()
        print(
            f"Paragraph {i}:"
        )

        print(
            text[:500]
        )

    print()
    print("=" * 80)
    print("LAST 5 PARAGRAPHS")
    print("=" * 80)

    for i, text in enumerate(
        paragraphs[-5:],
        1
    ):

        print()
        print(
            f"Paragraph {i}:"
        )

        print(
            text[:500]
        )


if __name__ == "__main__":
    main()
