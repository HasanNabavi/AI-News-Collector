import json
import html
import re
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

ALLOWED_HOSTS = {
    "www.bbc.co.uk",
    "bbc.co.uk",
    "www.bbc.com",
    "bbc.com",
}


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_valid_url(url):
    try:
        parts = urlsplit(url)

        if parts.scheme not in {"http", "https"}:
            return False

        hostname = (parts.hostname or "").lower()

        return hostname in ALLOWED_HOSTS

    except Exception:
        return False


def get_meta_content(soup, name=None, property_name=None):
    if name:
        tag = soup.find("meta", attrs={"name": name})
    elif property_name:
        tag = soup.find("meta", attrs={"property": property_name})
    else:
        return ""

    if tag:
        return clean_text(tag.get("content", ""))

    return ""


def extract_json_ld(soup):
    blocks = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    )

    results = []

    for block in blocks:
        raw = block.string or block.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)
            results.append(data)
        except Exception:
            continue

    return results


def find_article_schema(json_ld_data):
    for data in json_ld_data:
        candidates = []

        if isinstance(data, dict):
            candidates.append(data)

            graph = data.get("@graph")

            if isinstance(graph, list):
                candidates.extend(
                    item for item in graph
                    if isinstance(item, dict)
                )

        elif isinstance(data, list):
            candidates.extend(
                item for item in data
                if isinstance(item, dict)
            )

        for item in candidates:
            schema_type = item.get("@type", "")

            if isinstance(schema_type, list):
                schema_types = schema_type
            else:
                schema_types = [schema_type]

            if any(
                "NewsArticle" in str(item_type)
                or "Article" in str(item_type)
                for item_type in schema_types
            ):
                return item

    return {}


def extract_title(soup, article_schema):
    title = get_meta_content(
        soup,
        property_name="og:title"
    )

    if title:
        return title

    h1 = soup.find("h1")

    if h1:
        title = clean_text(
            h1.get_text(" ", strip=True)
        )

        if title:
            return title

    title = article_schema.get("headline", "")

    if title:
        return clean_text(title)

    if soup.title:
        return clean_text(
            soup.title.get_text()
        )

    return ""


def extract_author(article_schema, soup):
    author = article_schema.get("author", "")

    if isinstance(author, dict):
        author = author.get("name", "")

    elif isinstance(author, list):
        names = []

        for item in author:
            if isinstance(item, dict):
                name = item.get("name", "")
            else:
                name = str(item)

            name = clean_text(name)

            if name:
                names.append(name)

        if names:
            return ", ".join(names)

        author = ""

    author = clean_text(str(author))

    if author:
        return author

    byline = soup.select_one(
        "[data-testid*='byline'], "
        "[class*='byline'], "
        "[class*='Byline']"
    )

    if byline:
        text = clean_text(
            byline.get_text(" ", strip=True)
        )

        if text:
            return text

    return ""


def extract_published_at(article_schema, soup):
    published_at = article_schema.get(
        "datePublished",
        ""
    )

    if published_at:
        return clean_text(
            str(published_at)
        )

    time_tag = soup.find(
        "time",
        attrs={"datetime": True}
    )

    if time_tag:
        return clean_text(
            time_tag.get("datetime", "")
        )

    return ""


def extract_standfirst(article_schema, soup):
    description = get_meta_content(
        soup,
        name="description"
    )

    if description:
        return description

    description = get_meta_content(
        soup,
        property_name="og:description"
    )

    if description:
        return description

    description = article_schema.get(
        "description",
        ""
    )

    if description:
        return clean_text(
            str(description)
        )

    return ""


def extract_article(soup):
    article = soup.find("article")

    if article is not None:
        return article

    main = soup.find("main")

    if main is not None:
        return main

    return None


def extract_article_text(article, standfirst):
    if article is None:
        return ""

    # Work on an independent BeautifulSoup tree so that
    # removing elements does not modify the original page tree.
    article = BeautifulSoup(
        str(article),
        "html.parser"
    )

    # Remove elements that are clearly not part
    # of the article text.
    unwanted_selectors = [
        "script",
        "style",
        "noscript",
        "svg",
        "button",
        "nav",
        "[aria-hidden='true']",
    ]

    for selector in unwanted_selectors:
        for element in article.select(selector):
            element.decompose()

    # Remove media captions and video-player blocks.
    for element in article.find_all(
        ["figcaption", "video"]
    ):
        element.decompose()

    # BBC Related Articles / link blocks.
    #
    # The BBC page structure uses:
    #
    # <div data-block="links">
    #     ...
    #     <ul>
    #         <li><a>...</a></li>
    #         ...
    #     </ul>
    # </div>
    #
    # These blocks are not part of the article body.
    # Remove them structurally instead of trying to
    # identify them from their text content.
    for element in article.find_all(
        attrs={"data-block": "links"}
    ):
        element.decompose()

    # Remove remaining obvious promotional and
    # related-story containers.
    #
    # This is intentionally conservative and acts only
    # when the entire meaningful text of a container is
    # represented by its links.
    for element in article.find_all(
        ["section", "aside", "div"]
    ):
        links = element.find_all(
            "a",
            href=True
        )

        if not links:
            continue

        element_text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if not element_text:
            continue

        link_text_parts = []

        for link in links:
            link_text = clean_text(
                link.get_text(
                    " ",
                    strip=True
                )
            )

            if link_text:
                link_text_parts.append(
                    link_text
                )

        if not link_text_parts:
            continue

        link_text = clean_text(
            " ".join(link_text_parts)
        )

        # If all meaningful text in this container is
        # represented by links, it is likely a navigation
        # or related-story block rather than article prose.
        if link_text == element_text:
            element.decompose()

    paragraphs = []

    for element in article.find_all(
        ["p", "blockquote"]
    ):
        text = clean_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        # Remove paragraphs whose entire meaningful
        # content consists of links.
        links = element.find_all(
            "a",
            href=True
        )

        if links:
            link_text_parts = []

            for link in links:
                link_text = clean_text(
                    link.get_text(
                        " ",
                        strip=True
                    )
                )

                if link_text:
                    link_text_parts.append(
                        link_text
                    )

            link_text = clean_text(
                " ".join(link_text_parts)
            )

            if link_text == text:
                continue

        # Remove obvious video-player status messages.
        video_messages = {
            "this video can not be played",
            "this video cannot be played",
            "video player",
            "watch video"
        }

        if text.lower() in video_messages:
            continue

        # Remove exact duplicate paragraphs.
        if text in paragraphs:
            continue

        paragraphs.append(text)

    if not paragraphs:
        return ""

    # Remove trailing newsletter material.
    cleaned_paragraphs = []

    for text in paragraphs:
        lower_text = text.lower()

        if (
            "sign up for our" in lower_text
            or "sign up here" in lower_text
        ):
            break

        cleaned_paragraphs.append(text)

    paragraphs = cleaned_paragraphs

    if not paragraphs:
        return ""

    text = "\n\n".join(paragraphs)

    # Add standfirst only when it is not
    # already present.
    if standfirst and standfirst not in text:
        text = standfirst + "\n\n" + text

    return text


def choose_srcset_image(srcset):
    if not srcset:
        return ""

    candidates = []

    for item in srcset.split(","):
        item = item.strip()

        if not item:
            continue

        parts = item.split()

        image_url = parts[0]

        width = 0

        if len(parts) > 1:
            match = re.match(
                r"(\d+)w",
                parts[1]
            )

            if match:
                width = int(
                    match.group(1)
                )

        candidates.append(
            (width, image_url)
        )

    if not candidates:
        return ""

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def extract_images(soup, article, main_image):
    images = []

    if main_image:
        images.append(main_image)

    if article is None:
        return images

    for image in article.find_all("img"):
        src = ""

        srcset = (
            image.get("srcset")
            or image.get("data-srcset")
            or ""
        )

        if srcset:
            src = choose_srcset_image(
                srcset
            )

        if not src:
            src = (
                image.get("data-src")
                or image.get("data-lazy-src")
                or image.get("src")
                or ""
            )

        if not src:
            continue

        src = urljoin(
            "https://www.bbc.co.uk/",
            src
        )

        if src not in images:
            images.append(src)

    return images


def extract_videos(article):
    videos = []

    if article is None:
        return videos

    for video in article.find_all("video"):
        src = video.get("src")

        if src:
            videos.append(
                urljoin(
                    "https://www.bbc.co.uk/",
                    src
                )
            )

        for source in video.find_all(
            "source"
        ):
            src = source.get("src")

            if src:
                videos.append(
                    urljoin(
                        "https://www.bbc.co.uk/",
                        src
                    )
                )

    for iframe in article.find_all(
        "iframe"
    ):
        src = iframe.get(
            "src",
            ""
        )

        if (
            "youtube.com" in src
            or "youtu.be" in src
            or "vimeo.com" in src
        ):
            videos.append(
                urljoin(
                    "https://www.bbc.co.uk/",
                    src
                )
            )

    unique_videos = []

    for video in videos:
        if video not in unique_videos:
            unique_videos.append(video)

    return unique_videos


def scrape(url):
    if not is_valid_url(url):
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
            "error": "Invalid BBC URL."
        }

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        response = session.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        json_ld_data = extract_json_ld(
            soup
        )

        article_schema = find_article_schema(
            json_ld_data
        )

        title = extract_title(
            soup,
            article_schema
        )

        author = extract_author(
            article_schema,
            soup
        )

        published_at = extract_published_at(
            article_schema,
            soup
        )

        standfirst = extract_standfirst(
            article_schema,
            soup
        )

        article = extract_article(
            soup
        )

        text = extract_article_text(
            article,
            standfirst
        )

        main_image = get_meta_content(
            soup,
            property_name="og:image"
        )

        if not main_image:
            schema_image = article_schema.get(
                "image",
                ""
            )

            if isinstance(
                schema_image,
                list
            ):
                if schema_image:
                    schema_image = schema_image[0]

            if isinstance(
                schema_image,
                dict
            ):
                schema_image = (
                    schema_image.get(
                        "url",
                        ""
                    )
                )

            main_image = clean_text(
                str(schema_image)
            )

        if main_image:
            main_image = urljoin(
                url,
                main_image
            )

        images = extract_images(
            soup,
            article,
            main_image
        )

        videos = extract_videos(
            article
        )

        if not title:
            return {
                "page_type": "article",
                "title": "",
                "text": "",
                "author": author,
                "published_at": published_at,
                "standfirst": standfirst,
                "main_image": main_image,
                "images": images,
                "videos": videos,
                "url": url,
                "status": "error",
                "error": (
                    "Article title could not "
                    "be extracted."
                )
            }

        if len(text) < 100:
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
                "status": "error",
                "error": (
                    "Article text could not be "
                    "extracted or is too short."
                )
            }

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

    except Exception as error:
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
            "error": (
                f"Unexpected scraper error: {error}"
            )
        }


if __name__ == "__main__":
    print(
        "BBC Technology scraper loaded successfully."
    )
