import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
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


PLACEHOLDER_IMAGE_PATTERNS = (
    "grey-placeholder",
    "placeholder",
    "transparent.gif",
    "pixel.gif",
    "spacer.gif",
    "1x1",
)


VIDEO_URL_PATTERNS = (
    r"https?://[^\"'\s<>]+\.mp4(?:\?[^\"'\s<>]*)?",
    r"https?://[^\"'\s<>]+\.m3u8(?:\?[^\"'\s<>]*)?",
    r"https?://[^\"'\s<>]+\.webm(?:\?[^\"'\s<>]*)?",
)


def is_bbc_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return host in ALLOWED_HOSTS
    except Exception:
        return False


def is_iplayer_url(url):
    try:
        path = (urlparse(url).path or "").lower()
        return "/iplayer/" in path
    except Exception:
        return False


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_url(url, base_url):
    if not url:
        return ""

    url = url.strip()

    if url.startswith("//"):
        return "https:" + url

    return urljoin(base_url, url)


def extract_json_script(soup, script_id):
    script = soup.find("script", id=script_id)

    if not script:
        return None

    raw = script.string or script.get_text()

    if not raw:
        return None

    try:
        return json.loads(raw)
    except Exception:
        return None


def extract_next_data(soup):
    return extract_json_script(soup, "__NEXT_DATA__")


def extract_simorgh_data(soup):
    scripts = soup.find_all("script")

    for script in scripts:
        raw = script.string or script.get_text()

        if not raw:
            continue

        if "SIMORGH_DATA" not in raw:
            continue

        match = re.search(
            r"window\s*\.\s*SIMORGH_DATA\s*=\s*(\{.*\})\s*;?\s*$",
            raw,
            re.DOTALL,
        )

        if not match:
            match = re.search(
                r"SIMORGH_DATA\s*=\s*(\{.*\})",
                raw,
                re.DOTALL,
            )

        if not match:
            continue

        try:
            return json.loads(match.group(1))
        except Exception:
            continue

    return None


def recursive_walk(value):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from recursive_walk(child)

    elif isinstance(value, list):
        for item in value:
            yield from recursive_walk(item)


def find_article_schema(json_ld):
    if not json_ld:
        return None

    items = json_ld if isinstance(json_ld, list) else [json_ld]

    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = item.get("@type", "")

        if isinstance(item_type, list):
            types = [str(x).lower() for x in item_type]
        else:
            types = [str(item_type).lower()]

        if any(
            x in types
            for x in (
                "article",
                "newsarticle",
                "reportagenewsarticle",
                "analysisnewsarticle",
            )
        ):
            return item

        graph = item.get("@graph")

        if isinstance(graph, list):
            result = find_article_schema(graph)

            if result:
                return result

    return None


def extract_json_ld(soup):
    results = []

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        raw = script.string or script.get_text()

        if not raw:
            continue

        try:
            data = json.loads(raw)
            results.append(data)
        except Exception:
            continue

    return results


def extract_title(soup, schema):
    value = soup.find("meta", property="og:title")

    if value and value.get("content"):
        return normalize_space(value["content"])

    h1 = soup.find("h1")

    if h1:
        text = normalize_space(h1.get_text(" ", strip=True))

        if text:
            return text

    if schema:
        headline = schema.get("headline")

        if headline:
            return normalize_space(headline)

    title = soup.find("title")

    if title:
        return normalize_space(title.get_text(" ", strip=True))

    return ""


def extract_author(soup, schema):
    if schema:
        author = schema.get("author")

        if isinstance(author, dict):
            name = author.get("name")

            if name:
                return normalize_space(name)

        if isinstance(author, list):
            names = []

            for item in author:
                if isinstance(item, dict) and item.get("name"):
                    names.append(normalize_space(item["name"]))
                elif isinstance(item, str):
                    names.append(normalize_space(item))

            if names:
                return ", ".join(dict.fromkeys(names))

        if isinstance(author, str):
            return normalize_space(author)

    selectors = [
        "[rel='author']",
        "[data-testid*='byline']",
        "[class*='byline']",
        "[class*='Byline']",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if not element:
            continue

        text = normalize_space(element.get_text(" ", strip=True))

        if not text:
            continue

        text = re.sub(
            r"^(By|Written by|Reporter|Correspondent)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        if text:
            return text

    return ""


def extract_published_at(soup, schema):
    if schema:
        value = (
            schema.get("datePublished")
            or schema.get("dateCreated")
            or schema.get("dateModified")
        )

        if value:
            return str(value)

    time_tag = soup.find("time")

    if time_tag:
        value = time_tag.get("datetime")

        if value:
            return value

    return ""


def extract_standfirst(soup, schema):
    if schema:
        value = schema.get("description")

        if value:
            return normalize_space(value)

    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
    ):
        tag = soup.find("meta", attrs=attrs)

        if tag and tag.get("content"):
            return normalize_space(tag["content"])

    selectors = [
        "[data-testid='standfirst']",
        "[class*='standfirst']",
        "[class*='Standfirst']",
        "[class*='summary']",
        "[class*='Summary']",
    ]

    for selector in selectors:
        element = soup.select_one(selector)

        if element:
            text = normalize_space(element.get_text(" ", strip=True))

            if text:
                return text

    return ""


def remove_standfirst_from_text(text, standfirst):
    text = text.strip()
    standfirst = normalize_space(standfirst)

    if not text or not standfirst:
        return text

    paragraphs = text.split("\n\n")

    if paragraphs:
        first = normalize_space(paragraphs[0])

        if first == standfirst:
            paragraphs = paragraphs[1:]

    return "\n\n".join(
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    )


def clean_article_paragraphs(paragraphs, standfirst=""):
    cleaned = []
    seen = set()

    for paragraph in paragraphs:
        paragraph = normalize_space(paragraph)

        if not paragraph:
            continue

        if len(paragraph) < 2:
            continue

        if paragraph.lower() in {
            "advertisement",
            "advertising",
            "watch",
            "listen",
            "read more",
            "related",
        }:
            continue

        key = paragraph.casefold()

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(paragraph)

    text = "\n\n".join(cleaned)

    return remove_standfirst_from_text(text, standfirst)


def extract_article_text_from_dom(soup, standfirst):
    article = soup.find("article")

    if not article:
        article = soup.find("main")

    if not article:
        return ""

    article_copy = BeautifulSoup(
        str(article),
        "html.parser",
    )

    for tag in article_copy.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "button",
            "nav",
            "footer",
            "form",
        ]
    ):
        tag.decompose()

    for element in article_copy.find_all(
        attrs={"aria-hidden": "true"}
    ):
        element.decompose()

    for element in article_copy.find_all(
        ["video", "audio", "iframe"]
    ):
        element.decompose()

    for element in article_copy.find_all(
        attrs={"data-block": "links"}
    ):
        element.decompose()

    paragraphs = []

    for element in article_copy.find_all(
        ["p", "blockquote"]
    ):
        text = normalize_space(
            element.get_text(" ", strip=True)
        )

        if not text:
            continue

        links_text = normalize_space(
            " ".join(
                link.get_text(" ", strip=True)
                for link in element.find_all("a")
            )
        )

        if links_text and links_text == text:
            continue

        if re.match(
            r"^(Advertisement|Watch|Listen|Read more)\b",
            text,
            flags=re.IGNORECASE,
        ):
            continue

        paragraphs.append(text)

    result = clean_article_paragraphs(
        paragraphs,
        standfirst,
    )

    cutoff_patterns = [
        r"^sign up for our newsletter",
        r"^get the latest news",
        r"^follow bbc",
        r"^more on this story",
    ]

    final_paragraphs = []

    for paragraph in result.split("\n\n"):
        if any(
            re.search(pattern, paragraph, re.IGNORECASE)
            for pattern in cutoff_patterns
        ):
            break

        final_paragraphs.append(paragraph)

    return "\n\n".join(final_paragraphs)


def extract_text_from_block(block):
    if isinstance(block, str):
        return normalize_space(block)

    if not isinstance(block, dict):
        return ""

    texts = []

    for key in (
        "text",
        "value",
        "plainText",
    ):
        value = block.get(key)

        if isinstance(value, str):
            text = normalize_space(value)

            if text:
                texts.append(text)

    model = block.get("model")

    if isinstance(model, dict):
        model_text = extract_text_from_block(model)

        if model_text:
            texts.append(model_text)

    blocks = block.get("blocks")

    if isinstance(blocks, list):
        for child in blocks:
            child_text = extract_text_from_block(child)

            if child_text:
                texts.append(child_text)

    return "\n\n".join(dict.fromkeys(texts))


def collect_block_lists(data):
    candidates = []

    for obj in recursive_walk(data):
        if not isinstance(obj, dict):
            continue

        blocks = obj.get("blocks")

        if not isinstance(blocks, list):
            continue

        if not blocks:
            continue

        score = 0

        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = str(
                block.get("type")
                or block.get("blockType")
                or ""
            ).lower()

            if block_type in {
                "paragraph",
                "text",
                "heading",
                "subheading",
                "image",
                "video",
                "legacyMedia",
                "legacy_media",
            }:
                score += 3

        if score > 0:
            candidates.append((score, blocks))

    return candidates


def extract_text_from_bbc_blocks(data, standfirst):
    candidates = collect_block_lists(data)

    if not candidates:
        return ""

    scored = []

    for score, blocks in candidates:
        paragraphs = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = str(
                block.get("type")
                or block.get("blockType")
                or ""
            ).lower()

            if block_type in {
                "paragraph",
                "text",
                "heading",
                "subheading",
            }:
                text = extract_text_from_block(block)

                if text:
                    paragraphs.append(text)

        cleaned = clean_article_paragraphs(
            paragraphs,
            standfirst,
        )

        if len(cleaned) >= 100:
            scored.append(
                (
                    len(cleaned),
                    score,
                    cleaned,
                )
            )

    if not scored:
        return ""

    scored.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )

    return scored[0][2]


def extract_article_text_from_json(
    next_data,
    simorgh_data,
    standfirst,
):
    candidates = []

    if next_data:
        text = extract_text_from_bbc_blocks(
            next_data,
            standfirst,
        )

        if len(text) >= 100:
            candidates.append(text)

    if simorgh_data:
        text = extract_text_from_bbc_blocks(
            simorgh_data,
            standfirst,
        )

        if len(text) >= 100:
            candidates.append(text)

    if not candidates:
        return ""

    return max(
        candidates,
        key=len,
    )


def is_placeholder_image(url):
    lower = url.lower()

    return any(
        pattern in lower
        for pattern in PLACEHOLDER_IMAGE_PATTERNS
    )


def image_identity(url):
    value = url.lower()

    value = re.sub(
        r"\?.*$",
        "",
        value,
    )

    value = re.sub(
        r"/\d+/[^/]+/",
        "/",
        value,
    )

    value = value.replace(
        ".webp",
        "",
    )

    return value


def extract_images(soup, schema, base_url):
    images = []

    if schema:
        image_data = schema.get("image")

        if isinstance(image_data, str):
            images.append(
                normalize_url(
                    image_data,
                    base_url,
                )
            )

        elif isinstance(image_data, dict):
            value = (
                image_data.get("url")
                or image_data.get("contentUrl")
            )

            if value:
                images.append(
                    normalize_url(
                        value,
                        base_url,
                    )
                )

        elif isinstance(image_data, list):
            for item in image_data:
                if isinstance(item, str):
                    images.append(
                        normalize_url(
                            item,
                            base_url,
                        )
                    )
                elif isinstance(item, dict):
                    value = (
                        item.get("url")
                        or item.get("contentUrl")
                    )

                    if value:
                        images.append(
                            normalize_url(
                                value,
                                base_url,
                            )
                        )

    for meta in soup.find_all(
        "meta",
        property=re.compile(
            r"^og:image$",
            re.IGNORECASE,
        ),
    ):
        content = meta.get("content")

        if content:
            images.append(
                normalize_url(
                    content,
                    base_url,
                )
            )

    for image in soup.find_all("img"):
        candidates = []

        srcset = image.get("srcset")

        if srcset:
            for item in srcset.split(","):
                url = item.strip().split(" ")[0]

                if url:
                    candidates.append(url)

        for attr in (
            "data-src",
            "data-lazy-src",
            "data-original",
            "src",
        ):
            value = image.get(attr)

            if value:
                candidates.append(value)

        for candidate in candidates:
            normalized = normalize_url(
                candidate,
                base_url,
            )

            if normalized:
                images.append(normalized)

    result = []
    seen = set()

    for image_url in images:
        if not image_url:
            continue

        if image_url.startswith("data:"):
            continue

        if is_placeholder_image(image_url):
            continue

        identity = image_identity(image_url)

        if identity in seen:
            continue

        seen.add(identity)
        result.append(image_url)

    return result


def find_media_url(value):
    if isinstance(value, str):
        for pattern in VIDEO_URL_PATTERNS:
            match = re.search(
                pattern,
                value,
                re.IGNORECASE,
            )

            if match:
                return match.group(0)

        return ""

    if isinstance(value, dict):
        for key in (
            "url",
            "src",
            "uri",
            "mediaUrl",
            "videoUrl",
            "contentUrl",
        ):
            candidate = value.get(key)

            if isinstance(candidate, str):
                if (
                    candidate.startswith("http://")
                    or candidate.startswith("https://")
                ):
                    if any(
                        extension in candidate.lower()
                        for extension in (
                            ".mp4",
                            ".m3u8",
                            ".webm",
                        )
                    ):
                        return candidate

        for child in value.values():
            result = find_media_url(child)

            if result:
                return result

    elif isinstance(value, list):
        for item in value:
            result = find_media_url(item)

            if result:
                return result

    return ""


def extract_videos_from_json(data, base_url):
    videos = []

    if not data:
        return videos

    for obj in recursive_walk(data):
        if not isinstance(obj, dict):
            continue

        block_type = str(
            obj.get("type")
            or obj.get("blockType")
            or ""
        ).lower()

        if block_type not in {
            "video",
            "legacymedia",
            "media",
        }:
            continue

        model = obj.get(
            "model",
            obj,
        )

        video_url = find_media_url(model)

        if video_url:
            videos.append(
                normalize_url(
                    video_url,
                    base_url,
                )
            )

    return videos


def extract_videos_from_dom(soup, base_url):
    videos = []

    for video in soup.find_all("video"):
        for source in video.find_all("source"):
            src = source.get("src")

            if src:
                videos.append(
                    normalize_url(
                        src,
                        base_url,
                    )
                )

        src = video.get("src")

        if src:
            videos.append(
                normalize_url(
                    src,
                    base_url,
                )
            )

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")

        if not src:
            continue

        lower = src.lower()

        if (
            "youtube.com" in lower
            or "youtu.be" in lower
            or "vimeo.com" in lower
            or "bbc.co.uk" in lower
            or "bbc.com" in lower
        ):
            videos.append(
                normalize_url(
                    src,
                    base_url,
                )
            )

    return videos


def extract_videos(
    soup,
    next_data,
    simorgh_data,
    base_url,
):
    videos = []

    videos.extend(
        extract_videos_from_json(
            next_data,
            base_url,
        )
    )

    videos.extend(
        extract_videos_from_json(
            simorgh_data,
            base_url,
        )
    )

    videos.extend(
        extract_videos_from_dom(
            soup,
            base_url,
        )
    )

    result = []
    seen = set()

    for video in videos:
        if not video:
            continue

        identity = re.sub(
            r"\?.*$",
            "",
            video.lower(),
        )

        if identity in seen:
            continue

        seen.add(identity)
        result.append(video)

    return result


def build_result(
    url,
    title="",
    text="",
    author="",
    published_at="",
    standfirst="",
    main_image="",
    images=None,
    videos=None,
    page_type="article",
    status="success",
    error="",
):
    images = images or []
    videos = videos or []

    return {
        "url": url,
        "title": title,
        "scraped_data": {
            "text": text,
            "author": author,
            "published_at": published_at,
            "standfirst": standfirst,
            "main_image": main_image,
            "images": images,
            "videos": videos,
        },
        "page_type": page_type,
        "status": status,
        "error": error,
    }


def scrape(url):
    if not is_bbc_url(url):
        return build_result(
            url=url,
            page_type="unsupported",
            status="error",
            error="URL is not a supported BBC domain.",
        )

    if is_iplayer_url(url):
        return build_result(
            url=url,
            page_type="video",
            status="unsupported",
            error="BBC iPlayer pages are not supported by this scraper.",
        )

    try:
        response = requests.get(
            url,
            headers=BASE_HEADERS,
            timeout=30,
        )

        response.raise_for_status()

    except Exception as exc:
        return build_result(
            url=url,
            status="error",
            error=f"Request failed: {exc}",
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    json_ld = extract_json_ld(soup)
    schema = find_article_schema(json_ld)

    next_data = extract_next_data(soup)
    simorgh_data = extract_simorgh_data(soup)

    title = extract_title(
        soup,
        schema,
    )

    author = extract_author(
        soup,
        schema,
    )

    published_at = extract_published_at(
        soup,
        schema,
    )

    standfirst = extract_standfirst(
        soup,
        schema,
    )

    text = extract_article_text_from_json(
        next_data,
        simorgh_data,
        standfirst,
    )

    if len(text) < 100:
        text = extract_article_text_from_dom(
            soup,
            standfirst,
        )

    images = extract_images(
        soup,
        schema,
        url,
    )

    videos = extract_videos(
        soup,
        next_data,
        simorgh_data,
        url,
    )

    main_image = images[0] if images else ""

    if len(text) < 100:
        return build_result(
            url=url,
            title=title,
            text=text,
            author=author,
            published_at=published_at,
            standfirst=standfirst,
            main_image=main_image,
            images=images,
            videos=videos,
            page_type="article",
            status="error",
            error=(
                "Article text could not be extracted "
                "or is too short."
            ),
        )

    return build_result(
        url=url,
        title=title,
        text=text,
        author=author,
        published_at=published_at,
        standfirst=standfirst,
        main_image=main_image,
        images=images,
        videos=videos,
        page_type="article",
        status="success",
        error="",
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "URL argument is required.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)

    result = scrape(sys.argv[1])

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )
