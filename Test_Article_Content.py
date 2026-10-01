import json
import re
import requests
import feedparser
from bs4 import BeautifulSoup


TEST_SOURCES = [
    "MIT Technology Review",
    "TechCrunch",
    "BBC Technology"
]


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def get_article_from_rss(source):

    feed = feedparser.parse(
        source["rss_url"]
    )

    if not feed.entries:
        return None

    item = feed.entries[0]

    return {
        "title": item.get("title", ""),
        "url": item.get("link", "")
    }


def get_candidates(soup):

    candidates = []

    for tag in soup.find_all(
        ["article", "main", "section", "div"]
    ):

        paragraphs = []

        for p in tag.find_all("p"):

            text = normalize_text(
                p.get_text(
                    " ",
                    strip=True
                )
            )

            if len(text) >= 80:
                paragraphs.append(p)

        if len(paragraphs) < 5:
            continue

        full_text = normalize_text(
            " ".join(
                p.get_text(
                    " ",
                    strip=True
                )
                for p in paragraphs
            )
        )

        if len(full_text) < 1000:
            continue

        candidates.append({
            "tag": tag,
            "paragraphs": paragraphs,
            "text": full_text
        })

    return candidates


def title_coverage(title, text):

    title_words = set(
        re.findall(
            r"\w+",
            title.lower()
        )
    )

    text_words = set(
        re.findall(
            r"\w+",
            text.lower()
        )
    )

    if not title_words:
        return 0

    return len(
        title_words & text_words
    ) / len(title_words)


def describe_paragraph(p, number):

    text = normalize_text(
        p.get_text(
            " ",
            strip=True
        )
    )

    links = len(
        p.find_all("a")
    )

    parent = p.parent

    parent_name = (
        parent.name
        if parent
        else ""
    )

    parent_class = ""

    if parent:
        parent_class = " ".join(
            parent.get(
                "class",
                []
            )
        )

    print(
        f"{number:02d}. "
        f"len={len(text):4d} "
        f"links={links} "
        f"parent={parent_name}"
        f".{parent_class[:35]}"
    )

    print(
        f"    {text[:220]}"
    )


def analyze_source(
    source_name,
    article
):

    print()
    print("#" * 90)
    print(
        f"SOURCE: {source_name}"
    )
    print(
        f"TITLE: {article['title']}"
    )
    print("#" * 90)

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
        article["url"],
        headers=headers,
        timeout=30
    )

    print(
        f"HTTP: {response.status_code}"
    )

    if response.status_code != 200:
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    candidates = get_candidates(
        soup
    )

    # Remove near-duplicate containers.
    unique_candidates = []

    seen = set()

    for candidate in candidates:

        paragraph_count = len(
            candidate["paragraphs"]
        )

        text_length = len(
            candidate["text"]
        )

        key = (
            paragraph_count,
            text_length
        )

        if key in seen:
            continue

        seen.add(key)

        unique_candidates.append(
            candidate
        )

    # Sort from smaller to larger.
    unique_candidates.sort(
        key=lambda x: len(
            x["paragraphs"]
        )
    )

    print(
        f"Unique candidates: "
        f"{len(unique_candidates)}"
    )

    # We inspect only three candidates:
    # small / middle / large.

    indexes = []

    if unique_candidates:
        indexes.append(0)

    if len(unique_candidates) > 2:
        indexes.append(
            len(unique_candidates) // 2
        )

    if len(unique_candidates) > 1:
        indexes.append(
            len(unique_candidates) - 1
        )

    for candidate_number, index in enumerate(
        indexes,
        start=1
    ):

        candidate = unique_candidates[index]

        tag = candidate["tag"]

        tag_description = tag.name

        if tag.get("id"):
            tag_description += (
                f"#{tag.get('id')}"
            )

        classes = tag.get(
            "class",
            []
        )

        if classes:
            tag_description += (
                "."
                + ".".join(classes[:3])
            )

        coverage = title_coverage(
            article["title"],
            candidate["text"]
        )

        print()
        print(
            "-" * 90
        )

        print(
            f"CANDIDATE {candidate_number}"
        )

        print(
            f"Container: "
            f"{tag_description[:100]}"
        )

        print(
            f"Paragraphs: "
            f"{len(candidate['paragraphs'])}"
        )

        print(
            f"Text length: "
            f"{len(candidate['text'])}"
        )

        print(
            f"Title coverage: "
            f"{coverage:.2f}"
        )

        print(
            "Paragraphs:"
        )

        paragraphs = candidate[
            "paragraphs"
        ]

        # Show ALL paragraphs, but only
        # first 220 characters each.

        for number, p in enumerate(
            paragraphs,
            start=1
        ):
            describe_paragraph(
                p,
                number
            )


def main():

    sources = []

    with open(
        "A_Source.json",
        "r",
        encoding="utf-8"
    ) as file:

        sources = json.load(
            file
        )["sources"]

    for source in sources:

        if source["name"] not in TEST_SOURCES:
            continue

        article = get_article_from_rss(
            source
        )

        if article is None:
            continue

        analyze_source(
            source["name"],
            article
        )


if __name__ == "__main__":
    main()
