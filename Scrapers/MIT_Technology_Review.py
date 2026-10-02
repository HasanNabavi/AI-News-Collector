import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def clean_text(text):
    """
    Clean and normalize extracted text.
    """

    return " ".join(
        text.split()
    )


def get_meta_content(soup, name=None, property_name=None):
    """
    Get content from a meta tag.
    """

    if name:
        tag = soup.find(
            "meta",
            attrs={"name": name}
        )

    elif property_name:
        tag = soup.find(
            "meta",
            attrs={"property": property_name}
        )

    else:
        return ""

    if tag:
        return tag.get(
            "content",
            ""
        ).strip()

    return ""


def extract_title(soup):
    """
    Extract article title.
    """

    title = get_meta_content(
        soup,
        property_name="og:title"
    )

    if title:
        return title

    if soup.title:
        return clean_text(
            soup.title.get_text()
        )

    return ""


def extract_author(soup):
    """
    Extract article author.
    """

    author = get_meta_content(
        soup,
        name="author"
    )

    if author:
        return author

    author = get_meta_content(
        soup,
        property_name="article:author"
    )

    if author:
        return author

    return ""


def extract_published_at(soup):
    """
    Extract article publication date.
    """

    # Method 1: article:published_time
    published_at = get_meta_content(
        soup,
        property_name="article:published_time"
    )

    if published_at:
        return published_at

    # Method 2: <time datetime="...">
    time_tag = soup.find(
        "time",
        attrs={"datetime": True}
    )

    if time_tag:
        return time_tag.get(
            "datetime",
            ""
        ).strip()

    # Method 3: JSON-LD
    json_ld_blocks = soup.find_all(
        "script",
        attrs={
            "type": "application/ld+json"
        }
    )

    for block in json_ld_blocks:

        try:
            import json

            data = json.loads(
                block.string
                or block.get_text()
            )

            if isinstance(data, dict):

                published_at = (
                    data.get("datePublished")
                    or data.get("dateCreated")
                )

                if published_at:
                    return published_at

        except Exception:
            continue

    return ""


def extract_standfirst(soup):
    """
    Extract article standfirst / dek / subtitle.
    """

    # Method 1: meta description
    standfirst = get_meta_content(
        soup,
        name="description"
    )

    if standfirst:
        return clean_text(
            standfirst
        )

    # Method 2: Open Graph description
    standfirst = get_meta_content(
        soup,
        property_name="og:description"
    )

    if standfirst:
        return clean_text(
            standfirst
        )

    # Method 3: page elements
    selectors = [
        "[class*='standfirst']",
        "[class*='Standfirst']",
        "[class*='dek']",
        "[class*='Dek']",
        "[class*='subtitle']",
        "[class*='Subtitle']",
        "[class*='intro']",
        "[class*='Intro']"
    ]

    for selector in selectors:

        element = soup.select_one(
            selector
        )

        if element:
            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if text:
                return text

    return ""


def is_newsletter_page(soup, title):
    """
    Detect MIT Technology Review newsletter / digest pages.

    These pages are intentionally skipped because they
    aggregate multiple stories rather than representing
    one independent news article.
    """

    title_lower = title.lower()

    newsletter_words = [
        "the download",
        "newsletter",
        "morning briefing",
        "daily newsletter"
    ]

    for word in newsletter_words:

        if word in title_lower:
            return True

    page_text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    ).lower()

    newsletter_markers = [
        "subscribe to the download",
        "sign up for the newsletter",
        "subscribe to our newsletter"
    ]

    for marker in newsletter_markers:

        if marker in page_text:
            return True

    return False


def remove_non_article_elements(content):
    """
    Remove elements that should not be included
    in the article body.
    """

    unwanted_keywords = [
        "related",
        "recommended",
        "newsletter",
        "subscribe",
        "social",
        "share",
        "author",
        "advert",
        "promo"
    ]

    for element in content.find_all(True):

        attributes = element.attrs or {}

        classes = attributes.get(
            "class",
            []
        )

        if isinstance(classes, list):
            classes = " ".join(
                classes
            )

        else:
            classes = str(
                classes
            )

        element_id = attributes.get(
            "id",
            ""
        )

        if element_id is None:
            element_id = ""

        combined = (
            classes
            + " "
            + str(element_id)
        ).lower()

        if any(
            keyword in combined
            for keyword in unwanted_keywords
        ):
            element.decompose()


def extract_article_text(
    soup,
    standfirst
):
    """
    Extract the main article text.
    """

    content = soup.select_one(
        "#content--body"
    )

    if content is None:
        return ""

    remove_non_article_elements(
        content
    )

    paragraphs = []

    for element in content.find_all(
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

        if text:
            paragraphs.append(
                text
            )

    text = "\n\n".join(
        paragraphs
    )

    if (
        standfirst
        and standfirst not in text
    ):
        text = (
            standfirst
            + "\n\n"
            + text
        )

    return text


def extract_images(soup):
    """
    Extract article images.
    """

    images = []

    # Main Open Graph image
    main_image = get_meta_content(
        soup,
        property_name="og:image"
    )

    if main_image:
        images.append(
            main_image
        )

    # Images inside article body
    content = soup.select_one(
        "#content--body"
    )

    if content:

        for image in content.find_all(
            "img"
        ):

            src = (
                image.get("src")
                or image.get(
                    "data-src"
                )
                or image.get(
                    "data-lazy-src"
                )
            )

            if src:
                images.append(
                    src
                )

    # Remove duplicates
    unique_images = []

    for image in images:

        if image not in unique_images:
            unique_images.append(
                image
            )

    return unique_images


def extract_videos(soup):
    """
    Extract video URLs.
    """

    videos = []

    # HTML5 video
    for video in soup.find_all(
        "video"
    ):

        src = video.get(
            "src"
        )

        if src:
            videos.append(
                src
            )

        for source in video.find_all(
            "source"
        ):

            source_url = source.get(
                "src"
            )

            if source_url:
                videos.append(
                    source_url
                )

    # YouTube / Vimeo iframes
    for iframe in soup.find_all(
        "iframe"
    ):

        src = iframe.get(
            "src",
            ""
        )

        if (
            "youtube.com"
            in src
            or "youtu.be"
            in src
            or "vimeo.com"
            in src
        ):
            videos.append(
                src
            )

    # Remove duplicates
    unique_videos = []

    for video in videos:

        if video not in unique_videos:
            unique_videos.append(
                video
            )

    return unique_videos


def scrape(url):
    """
    Scrape one MIT Technology Review article.

    Returns a standardized dictionary that can later
    be used by the Scraper Manager.
    """

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:

        return {
            "page_type": "",
            "title": "",
            "text": "",
            "author": "",
            "published_at": "",
            "standfirst": "",
            "main_image": "",
            "images": [],
            "videos": [],
            "url": url,
            "status": "error",
            "error": str(error)
        }

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title = extract_title(
        soup
    )

    # Skip newsletter / digest pages
    if is_newsletter_page(
        soup,
        title
    ):

        return {
            "page_type": "newsletter",
            "title": title,
            "text": "",
            "author": "",
            "published_at": "",
            "standfirst": "",
            "main_image": "",
            "images": [],
            "videos": [],
            "url": url,
            "status": "skipped"
        }

    author = extract_author(
        soup
    )

    published_at = extract_published_at(
        soup
    )

    standfirst = extract_standfirst(
        soup
    )

    text = extract_article_text(
        soup,
        standfirst
    )

    images = extract_images(
        soup
    )

    videos = extract_videos(
        soup
    )

    main_image = (
        images[0]
        if images
        else ""
    )

    return {
        "page_type": "article",
        "title": title,
        "text": text,
        "author": author,
        "published_at": published_at,
        "standfirst": standfirst,
        "main_image": main_image,
        "images": images,
        "videos": videos,
        "url": url,
        "status": "success"
    }
