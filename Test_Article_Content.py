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
            timeout=(10, 20)
        )

        print(
            f"HTTP status: {response.status_code}"
        )

        print(
            f"HTML length: {len(response.text)}"
        )

        return response.text

    except requests.Timeout:

        print(
            "Request timed out."
        )

        return None

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

    print()
    print("=" * 70)
    print("PARAGRAPH ANCESTOR ANALYSIS")
    print("=" * 70)

    sample_count = min(
        8,
        len(paragraphs)
    )

    for index in range(sample_count):

        paragraph = paragraphs[index]

        text = paragraph.get_text(
            " ",
            strip=True
        )

        print()
        print(
            f"Paragraph #{index + 1}"
        )

        print(
            f"Text preview: {text[:180]}"
        )

        ancestor = paragraph.parent

        level = 1

        while (
            ancestor is not None
            and level <= 6
        ):

            tag_name = ancestor.name

            element_id = ancestor.get(
                "id",
                ""
            )

            classes = ancestor.get(
                "class",
                []
            )

            if isinstance(
                classes,
                list
            ):
                class_text = " ".join(
                    classes
                )
            else:
                class_text = str(
                    classes
                )

            print(
                f"  Level {level}: "
                f"<{tag_name}> "
                f"id='{element_id}' "
                f"class='{class_text}'"
            )

            ancestor = ancestor.parent

            level += 1


def analyze_candidate_containers(soup):

    print()
    print("=" * 70)
    print("CANDIDATE CONTAINER ANALYSIS")
    print("=" * 70)

    candidates = []

    elements = soup.find_all(
        ["article", "main", "section", "div"]
    )

    for element in elements:

        paragraphs = element.find_all(
            "p"
        )

        if len(paragraphs) < 3:
            continue

        texts = []

        for paragraph in paragraphs:

            text = paragraph.get_text(
                " ",
                strip=True
            )

            if len(text) >= 80:
                texts.append(
                    text
                )

        if len(texts) < 3:
            continue

        total_text_length = sum(
            len(text)
            for text in texts
        )

        if total_text_length < 500:
            continue

        element_id = element.get(
            "id",
            ""
        )

        classes = element.get(
            "class",
            []
        )

        if isinstance(
            classes,
            list
        ):
            class_text = " ".join(
                classes
            )
        else:
            class_text = str(
                classes
            )

        candidates.append(
            {
                "tag": element.name,
                "id": element_id,
                "class": class_text,
                "paragraphs": len(texts),
                "text_length": total_text_length
            }
        )

    candidates.sort(
        key=lambda item: (
            item["paragraphs"],
            item["text_length"]
        ),
        reverse=True
    )

    print()
    print(
        f"Candidate containers: "
        f"{len(candidates)}"
    )

    for index, candidate in enumerate(
        candidates[:20],
        start=1
    ):

        print()
        print(
            f"Candidate #{index}"
        )

        print(
            f"Tag: "
            f"{candidate['tag']}"
        )

        print(
            f"ID: "
            f"{candidate['id']}"
        )

        print(
            f"Class: "
            f"{candidate['class']}"
        )

        print(
            f"Paragraphs: "
            f"{candidate['paragraphs']}"
        )

        print(
            f"Text length: "
            f"{candidate['text_length']}"
        )


def test_source(source):

    print()
    print()
    print("#" * 70)
    print(
        f"SOURCE: {source['name']}"
    )
    print("#" * 70)

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
            "No RSS entries."
        )

        return

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
            "No article URL."
        )

        return

    print()
    print("Requesting article page...")

    html = get_article_page(
        url
    )

    if not html:
        return

    soup = BeautifulSoup(
        html,
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

        print(
            "Not found"
        )

    analyze_paragraph_ancestors(
        soup
    )

    analyze_candidate_containers(
        soup
    )


def main():

    print()
    print("=" * 70)
    print(
        "ARTICLE DOM STRUCTURE TEST"
    )
    print("=" * 70)

    for source in TEST_SOURCES:

        test_source(
            source
        )

    print()
    print("=" * 70)
    print(
        "ALL TESTS COMPLETED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
