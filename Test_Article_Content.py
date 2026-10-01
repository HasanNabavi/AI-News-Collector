import requests
import re
import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup


URL = (
    "https://www.technologyreview.com/"
    "2026/10/01/1145588/"
    "ai-mind-reading-reconstructs-"
    "what-youre-looking-at/"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def clean_text(text):
    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_meta_content(
    soup,
    **kwargs
):
    tag = soup.find(
        "meta",
        attrs=kwargs
    )

    if tag:
        return clean_text(
            tag.get(
                "content",
                ""
            )
        )

    return ""


def extract_title(soup):

    title = get_meta_content(
        soup,
        property="og:title"
    )

    if title:
        return title

    h1 = soup.find("h1")

    if h1:
        return clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

    return ""


def extract_author(soup):

    author = get_meta_content(
        soup,
        name="author"
    )

    if author:
        return author

    author = get_meta_content(
        soup,
        property="article:author"
    )

    if author:
        return author

    selectors = [
        "[class*='author']",
        "[class*='byline']"
    ]

    for selector in selectors:

        element = soup.select_one(
            selector
        )

        if not element:
            continue

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if text:

            text = re.sub(
                r"^by\s+",
                "",
                text,
                flags=re.IGNORECASE
            )

            return text

    return ""


def extract_published_at(soup):

    published = get_meta_content(
        soup,
        property="article:published_time"
    )

    if published:
        return published

    time_element = soup.find(
        "time",
        attrs={
            "datetime": True
        }
    )

    if time_element:
        return time_element.get(
            "datetime",
            ""
        )

    return ""


def is_newsletter_page(
    soup,
    title
):

    normalized_title = clean_text(
        title
    ).lower()

    newsletter_titles = [
        "the download:",
        "the spark:",
        "the algorithm:"
    ]

    for newsletter_title in newsletter_titles:

        if normalized_title.startswith(
            newsletter_title
        ):
            return True

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    ).lower()

    markers = [
        "this is today's edition of the download",
        "our weekday newsletter",
        "this article is from the spark",
        "weekly climate newsletter"
    ]

    for marker in markers:

        if marker in page_text:
            return True

    return False


def remove_non_article_elements(
    container
):

    keywords = [
        "related",
        "popular",
        "deepdive",
        "deep-dive",
        "share",
        "newsletter",
        "stay-connected",
        "footer",
        "recommended"
    ]

    elements = container.find_all(
        True
    )

    for element in elements:

        if not getattr(
            element,
            "attrs",
            None
        ):
            continue

        classes = " ".join(
            element.get(
                "class",
                []
            )
        ).lower()

        element_id = (
            element.get(
                "id",
                ""
            )
            or ""
        ).lower()

        combined = (
            classes
            + " "
            + element_id
        )

        if any(
            keyword in combined
            for keyword in keywords
        ):
            element.decompose()


def extract_article_text(
    soup
):

    container = soup.select_one(
        "#content--body"
    )

    if container is None:
        return ""

    container = BeautifulSoup(
        str(container),
        "html.parser"
    )

    remove_non_article_elements(
        container
    )

    paragraphs = []

    for element in container.find_all(
        [
            "p",
            "blockquote",
            "li"
        ]
    ):

        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        if len(text) < 20:
            continue

        paragraphs.append(
            text
        )

    cleaned_paragraphs = []

    for paragraph in paragraphs:

        if (
            cleaned_paragraphs
            and paragraph
            == cleaned_paragraphs[-1]
        ):
            continue

        cleaned_paragraphs.append(
            paragraph
        )

    return "\n\n".join(
        cleaned_paragraphs
    )


def extract_images(
    soup,
    article_url
):

    images = []

    og_image = get_meta_content(
        soup,
        property="og:image"
    )

    if og_image:

        images.append(
            urljoin(
                article_url,
                og_image
            )
        )

    container = soup.select_one(
        "#content--body"
    )

    if container:

        for image in container.find_all(
            "img"
        ):

            image_url = (
                image.get("src")
                or image.get(
                    "data-src"
                )
                or image.get(
                    "data-lazy-src"
                )
                or ""
            )

            if not image_url:
                continue

            image_url = urljoin(
                article_url,
                image_url
            )

            if image_url not in images:

                images.append(
                    image_url
                )

    main_image = (
        images[0]
        if images
        else ""
    )

    return main_image, images


def extract_videos(
    soup,
    article_url
):

    videos = []

    for video in soup.find_all(
        "video"
    ):

        source = video.find(
            "source"
        )

        video_url = ""

        if source:
            video_url = source.get(
                "src",
                ""
            )

        if not video_url:
            video_url = video.get(
                "src",
                ""
            )

        if video_url:

            video_url = urljoin(
                article_url,
                video_url
            )

            if video_url not in videos:
                videos.append(
                    video_url
                )

    for iframe in soup.find_all(
        "iframe"
    ):

        iframe_url = iframe.get(
            "src",
            ""
        )

        if not iframe_url:
            continue

        iframe_url = urljoin(
            article_url,
            iframe_url
        )

        lowered = iframe_url.lower()

        if (
            "youtube.com" in lowered
            or "youtu.be" in lowered
            or "vimeo.com" in lowered
        ):

            if iframe_url not in videos:
                videos.append(
                    iframe_url
                )

    return videos


def scrape(url):

    print(
        "Downloading page..."
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    print(
        f"HTTP status: {response.status_code}"
    )

    print(
        f"HTML length: {len(response.text)}"
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title = extract_title(
        soup
    )

    print(
        f"\nTitle:\n{title}"
    )

    if is_newsletter_page(
        soup,
        title
    ):

        print(
            "\nPAGE TYPE: NEWSLETTER"
        )

        print(
            "Status: SKIPPED"
        )

        return

    print(
        "\nPAGE TYPE: ARTICLE"
    )

    author = extract_author(
        soup
    )

    published_at = extract_published_at(
        soup
    )

    text = extract_article_text(
        soup
    )

    main_image, images = extract_images(
        soup,
        url
    )

    videos = extract_videos(
        soup,
        url
    )

    print(
        f"\nAuthor:\n{author}"
    )

    print(
        f"\nPublished:\n{published_at}"
    )

    print(
        "\nARTICLE TEXT"
    )

    print(
        "=" * 60
    )

    print(text)

    print(
        "=" * 60
    )

    print(
        f"\nText characters: {len(text)}"
    )

    print(
        f"Images found: {len(images)}"
    )

    print(
        f"Main image:\n{main_image}"
    )

    print(
        "\nAll images:"
    )

    for image in images:
        print(image)

    print(
        f"\nVideos found: {len(videos)}"
    )

    print(
        "\nVideos:"
    )

    for video in videos:
        print(video)

    result = {
        "page_type": "article",
        "title": title,
        "text": text,
        "author": author,
        "published_at": published_at,
        "main_image": main_image,
        "images": images,
        "videos": videos,
        "url": url
    }

    print(
        "\nJSON RESULT"
    )

    print(
        "=" * 60
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":

    scrape(URL)
