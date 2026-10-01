import json
import re
import requests
from bs4 import BeautifulSoup


TEST_SOURCES = [
    "MIT Technology Review",
    "TechCrunch",
    "BBC Technology"
]


def normalize_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def title_words(title):
    return set(
        re.findall(
            r"\w+",
            title.lower()
        )
    )


def title_coverage(title, text):
    title_set = title_words(title)

    if not title_set:
        return 0

    text_set = set(
        re.findall(
            r"\w+",
            text.lower()
        )
    )

    return len(
        title_set & text_set
    ) / len(title_set)


def get_candidate_containers(soup):
    candidates = []

    for tag in soup.find_all(
        ["article", "main", "section", "div"]
    ):

        paragraphs = []

        for p in tag.find_all("p"):
            text = normalize_text(
                p.get_text(" ", strip=True)
            )

            if len(text) >= 80:
                paragraphs.append(p)

        if len(paragraphs) < 5:
            continue

        text = normalize_text(
            " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
            )
        )

        if len(text) < 1000:
            continue

        candidates.append({
            "tag": tag,
            "paragraphs": paragraphs,
            "text": text
        })

    return candidates


def paragraph_metadata(p):
    text = normalize_text(
        p.get_text(
            " ",
            strip=True
        )
    )

    links = p.find_all("a")

    parent = p.parent

    parent_tag = (
        parent.name
        if parent
        else ""
    )

    parent_id = (
        parent.get("id", "")
        if parent
        else ""
    )

    parent_class = (
        " ".join(
            parent.get(
                "class",
                []
            )
        )
        if parent
        else ""
    )

    ancestors = []

    current = p.parent

    for _ in range(4):

        if current is None:
            break

        descriptor = current.name

        if current.get("id"):
            descriptor += (
                f"#{current.get('id')}"
            )

        classes = current.get(
            "class",
            []
        )

        if classes:
            descriptor += (
                "."
                + ".".join(classes[:2])
            )

        ancestors.append(
            descriptor
        )

        current = current.parent

    return {
        "text": text,
        "length": len(text),
        "links": len(links),
        "parent": (
            f"{parent_tag}"
            f"#{parent_id}"
            f".{parent_class}"
        ),
        "ancestors": ancestors
    }


def print_candidate(
    candidate_number,
    candidate,
    title
):

    paragraphs = candidate["paragraphs"]

    coverage = title_coverage(
        title,
        candidate["text"]
    )

    tag = candidate["tag"]

    tag_name = tag.name

    tag_id = tag.get(
        "id",
        ""
    )

    tag_class = " ".join(
        tag.get(
            "class",
            []
        )
    )

    print()
    print("=" * 100)

    print(
        f"CANDIDATE #{candidate_number}"
    )

    print(
        f"Container: "
        f"{tag_name}"
        f"#{tag_id}"
        f".{tag_class}"
    )

    print(
        f"Paragraphs: "
        f"{len(paragraphs)}"
    )

    print(
        f"Total text: "
        f"{len(candidate['text'])}"
    )

    print(
        f"Title coverage: "
        f"{coverage:.3f}"
    )

    print("=" * 100)

    for index, p in enumerate(
        paragraphs,
        start=1
    ):

        metadata = paragraph_metadata(p)

        print()
        print(
            f"[Paragraph {index}]"
        )

        print(
            f"Length: "
            f"{metadata['length']}"
        )

        print(
            f"Links: "
            f"{metadata['links']}"
        )

        print(
            f"Parent: "
            f"{metadata['parent']}"
        )

        print(
            "Ancestors:"
        )

        for ancestor in metadata[
            "ancestors"
        ]:
            print(
                f"  - {ancestor}"
            )

        print(
            "Text:"
        )

        print(
            metadata["text"]
        )


def test_source(
    source,
    url
):

    print()
    print()
    print("#" * 100)

    print(
        f"SOURCE: {source}"
    )

    print(
        f"URL: {url}"
    )

    print("#" * 100)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 "
            "Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print(
        f"HTTP status: "
        f"{response.status_code}"
    )

    if response.status_code != 200:
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title_tag = soup.find("title")

    title = normalize_text(
        title_tag.get_text()
        if title_tag
        else ""
    )

    print(
        f"Page title: {title}"
    )

    candidates = get_candidate_containers(
        soup
    )

    print(
        f"Candidate containers: "
        f"{len(candidates)}"
    )

    candidates.sort(
        key=lambda item: len(
            item["paragraphs"]
        )
    )

    # We intentionally inspect several
    # different container sizes.
    selected = []

    if candidates:

        selected.append(
            candidates[0]
        )

        if len(candidates) > 1:
            selected.append(
                candidates[len(candidates) // 2]
            )

        if len(candidates) > 2:
            selected.append(
                candidates[-1]
            )

    for index, candidate in enumerate(
        selected,
        start=1
    ):

        print_candidate(
            index,
            candidate,
            title
        )


def load_rss_sources():

    with open(
        "A_Source.json",
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data["sources"]


def get_first_article(
    source
):

    import feedparser

    feed = feedparser.parse(
        source["rss_url"]
    )

    if not feed.entries:
        return None

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


def main():

    sources = load_rss_sources()

    for source in sources:

        if source["name"] not in TEST_SOURCES:
            continue

        article = get_first_article(
            source
        )

        if article is None:
            print(
                f"No RSS article found: "
                f"{source['name']}"
            )

            continue

        test_source(
            source["name"],
            article["url"]
        )


if __name__ == "__main__":
    main()
