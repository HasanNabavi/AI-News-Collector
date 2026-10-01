import re
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


# ------------------------------------------------------
# HTTP
# ------------------------------------------------------

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

        if response.status_code != 200:
            return None

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


# ------------------------------------------------------
# Text normalization
# ------------------------------------------------------

def normalize_text(text):

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text
    )

    return text.strip()


def get_words(text):

    normalized = normalize_text(
        text
    )

    return set(
        normalized.split()
    )


# ------------------------------------------------------
# Title similarity
# ------------------------------------------------------

def title_similarity(
    article_title,
    candidate_text
):

    title_words = get_words(
        article_title
    )

    candidate_words = get_words(
        candidate_text
    )

    if not title_words:
        return 0

    intersection = (
        title_words
        &
        candidate_words
    )

    return (
        len(intersection)
        /
        len(title_words)
    )


# ------------------------------------------------------
# Paragraph extraction
# ------------------------------------------------------

def get_paragraphs(element):

    paragraphs = []

    for paragraph in element.find_all("p"):

        text = paragraph.get_text(
            " ",
            strip=True
        )

        if len(text) < 40:
            continue

        paragraphs.append(
            text
        )

    return paragraphs


# ------------------------------------------------------
# Candidate information
# ------------------------------------------------------

def analyze_candidate(
    element,
    article_title
):

    paragraphs = get_paragraphs(
        element
    )

    if len(paragraphs) < 3:
        return None

    full_text = "\n\n".join(
        paragraphs
    )

    if len(full_text) < 500:
        return None

    links = element.find_all(
        "a"
    )

    headings = element.find_all(
        ["h1", "h2", "h3", "h4"]
    )

    images = element.find_all(
        "img"
    )

    title_score = title_similarity(
        article_title,
        full_text
    )

    paragraph_count = len(
        paragraphs
    )

    text_length = len(
        full_text
    )

    link_count = len(
        links
    )

    heading_count = len(
        headings
    )

    image_count = len(
        images
    )

    # Text density relative to links.
    # Higher is generally better.

    link_text_length = 0

    for link in links:

        link_text = link.get_text(
            " ",
            strip=True
        )

        link_text_length += len(
            link_text
        )

    if text_length > 0:

        link_ratio = (
            link_text_length
            /
            text_length
        )

    else:

        link_ratio = 1

    # --------------------------------------------------
    # Candidate score
    # --------------------------------------------------

    score = 0

    # Strong signal:
    # article title words appear in container.

    score += title_score * 40

    # Longer coherent text gets some weight.

    if text_length >= 1500:
        score += 20

    elif text_length >= 1000:
        score += 15

    elif text_length >= 700:
        score += 10

    # Several paragraphs.

    if paragraph_count >= 10:
        score += 20

    elif paragraph_count >= 6:
        score += 15

    elif paragraph_count >= 3:
        score += 8

    # Penalize extremely link-heavy containers.

    if link_ratio < 0.10:
        score += 10

    elif link_ratio < 0.20:
        score += 5

    elif link_ratio > 0.50:
        score -= 15

    # Candidate with a huge number of headings
    # is less likely to be pure article text.

    if heading_count > 15:
        score -= 10

    return {
        "tag": element.name,
        "id": element.get(
            "id",
            ""
        ),
        "class": " ".join(
            element.get(
                "class",
                []
            )
        ),
        "paragraphs": paragraph_count,
        "text_length": text_length,
        "links": link_count,
        "headings": heading_count,
        "images": image_count,
        "link_ratio": round(
            link_ratio,
            3
        ),
        "title_score": round(
            title_score,
            3
        ),
        "score": round(
            score,
            2
        ),
        "first_text": paragraphs[0][:250],
        "last_text": paragraphs[-1][:400]
    }


# ------------------------------------------------------
# Find candidate containers
# ------------------------------------------------------

def find_candidates(
    soup,
    article_title
):

    candidates = []

    elements = soup.find_all(
        [
            "article",
            "main",
            "section",
            "div"
        ]
    )

    seen = set()

    for element in elements:

        result = analyze_candidate(
            element,
            article_title
        )

        if result is None:
            continue

        key = (
            result["tag"],
            result["id"],
            result["class"],
            result["paragraphs"],
            result["text_length"]
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result["element"] = element

        candidates.append(
            result
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates


# ------------------------------------------------------
# Print candidate
# ------------------------------------------------------

def print_candidate(
    number,
    candidate
):

    print()
    print(
        "-" * 70
    )

    print(
        f"CANDIDATE #{number}"
    )

    print(
        f"Score: "
        f"{candidate['score']}"
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

    print(
        f"Links: "
        f"{candidate['links']}"
    )

    print(
        f"Headings: "
        f"{candidate['headings']}"
    )

    print(
        f"Images: "
        f"{candidate['images']}"
    )

    print(
        f"Link ratio: "
        f"{candidate['link_ratio']}"
    )

    print(
        f"Title word coverage: "
        f"{candidate['title_score']}"
    )

    print()
    print(
        "FIRST TEXT:"
    )

    print(
        candidate["first_text"]
    )

    print()
    print(
        "LAST TEXT:"
    )

    print(
        candidate["last_text"]
    )


# ------------------------------------------------------
# Analyze source
# ------------------------------------------------------

def test_source(source):

    print()
    print()
    print(
        "#" * 70
    )

    print(
        f"SOURCE: {source['name']}"
    )

    print(
        "#" * 70
    )

    # --------------------------------------------------
    # RSS
    # --------------------------------------------------

    print()
    print(
        "Reading RSS..."
    )

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
    print(
        "Article title:"
    )

    print(
        title
    )

    print()
    print(
        "Article URL:"
    )

    print(
        url
    )

    if not url:
        return

    # --------------------------------------------------
    # Request
    # --------------------------------------------------

    print()
    print(
        "Requesting article page..."
    )

    html = get_article_page(
        url
    )

    if not html:
        return

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # --------------------------------------------------
    # Page title
    # --------------------------------------------------

    print()
    print(
        "Page title:"
    )

    if soup.title:

        print(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    # --------------------------------------------------
    # Find candidates
    # --------------------------------------------------

    print()
    print(
        "Analyzing candidate containers..."
    )

    candidates = find_candidates(
        soup,
        title
    )

    print()
    print(
        f"Valid candidates found: "
        f"{len(candidates)}"
    )

    # --------------------------------------------------
    # Show top candidates
    # --------------------------------------------------

    for index, candidate in enumerate(
        candidates[:8],
        start=1
    ):

        print_candidate(
            index,
            candidate
        )


# ------------------------------------------------------
# Main
# ------------------------------------------------------

def main():

    print()
    print(
        "=" * 70
    )

    print(
        "ARTICLE CONTAINER DISCOVERY TEST"
    )

    print(
        "=" * 70
    )

    for source in TEST_SOURCES:

        test_source(
            source
        )

    print()
    print(
        "=" * 70
    )

    print(
        "ALL TESTS COMPLETED"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":

    main()
