import requests
import trafilatura
import newspaper

from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
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


def is_iplayer_url(url):
    return "/iplayer/" in url.lower()


def empty_scraped_data():
    return {
        "text": "",
        "author": "",
        "published_at": "",
        "standfirst": "",
        "main_image": "",
        "images": [],
        "videos": [],
    }


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def extract_with_trafilatura(html, url):
    result = {
        "text": "",
        "author": "",
        "published_at": "",
        "title": "",
    }

    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            include_links=False,
        )

        if text:
            result["text"] = text.strip()
    except Exception:
        pass

    try:
        metadata = trafilatura.bare_extraction(
            html,
            url=url,
        )

        if metadata:
            data = metadata.as_dict()

            result["title"] = (data.get("title") or "").strip()
            result["author"] = (data.get("author") or "").strip()
            result["published_at"] = (
                data.get("date") or ""
            ).strip()

            structured_text = (
                data.get("text") or ""
            ).strip()

            if structured_text:
                result["text"] = structured_text

    except Exception:
        pass

    return result


def extract_with_newspaper(url):
    result = {
        "title": "",
        "text": "",
        "author": "",
        "published_at": "",
        "main_image": "",
        "images": [],
        "videos": [],
    }

    try:
        article = newspaper.article(
            url,
            language="en",
        )

        result["title"] = (
            article.title or ""
        ).strip()

        result["text"] = (
            article.text or ""
        ).strip()

        result["author"] = ", ".join(
            article.authors or []
        ).strip()

        if article.publish_date:
            result["published_at"] = str(
                article.publish_date
            )

        result["main_image"] = (
            article.top_image or ""
        ).strip()

        result["images"] = list(
            article.images or []
        )

        result["videos"] = list(
            article.movies or []
        )

    except Exception:
        pass

    return result


def extract_standfirst(soup):
    candidates = [
        soup.find(
            "meta",
            attrs={"property": "og:description"},
        ),
        soup.find(
            "meta",
            attrs={"name": "description"},
        ),
    ]

    for tag in candidates:
        if tag and tag.get("content"):
            return tag["content"].strip()

    return ""


def extract_title_from_html(soup):
    h1 = soup.find("h1")

    if h1:
        title = h1.get_text(
            " ",
            strip=True,
        )

        if title:
            return title

    og_title = soup.find(
        "meta",
        attrs={"property": "og:title"},
    )

    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    if soup.title:
        return soup.title.get_text(
            " ",
            strip=True,
        )

    return ""


def extract_images_from_html(soup, url):
    images = []

    for img in soup.find_all("img"):
        candidates = []

        for attribute in [
            "src",
            "data-src",
            "data-lazy-src",
            "data-original",
        ]:
            value = img.get(attribute)

            if value:
                candidates.append(value)

        srcset = img.get("srcset")

        if srcset:
            for item in srcset.split(","):
                item = item.strip()

                if item:
                    candidates.append(
                        item.split()[0]
                    )

        for image_url in candidates:
            image_url = urljoin(
                url,
                image_url,
            )

            if image_url.startswith(
                ("http://", "https://")
            ):
                if image_url not in images:
                    images.append(image_url)

    return images


def extract_videos_from_html(soup, url):
    videos = []

    for video in soup.find_all("video"):
        src = video.get("src")

        if src:
            videos.append(
                urljoin(url, src)
            )

        for source in video.find_all("source"):
            source_src = source.get("src")

            if source_src:
                videos.append(
                    urljoin(url, source_src)
                )

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")

        if not src:
            continue

        src = urljoin(url, src)

        lowered = src.lower()

        if (
            "youtube.com" in lowered
            or "youtu.be" in lowered
            or "vimeo.com" in lowered
            or "bbc.co.uk" in lowered
            or "bbc.com" in lowered
        ):
            videos.append(src)

    unique_videos = []

    for video in videos:
        if video not in unique_videos:
            unique_videos.append(video)

    return unique_videos


def scrape(url):
    if not url:
        return {
            "url": url,
            "title": "",
            "scraped_data": empty_scraped_data(),
            "page_type": "unknown",
            "status": "error",
            "error": "URL is empty.",
        }

    if is_iplayer_url(url):
        return {
            "url": url,
            "title": "",
            "scraped_data": empty_scraped_data(),
            "page_type": "video",
            "status": "unsupported",
            "error": (
                "BBC iPlayer pages are not supported "
                "by this scraper."
            ),
        }

    try:
        html = get_html(url)

    except Exception as e:
        return {
            "url": url,
            "title": "",
            "scraped_data": empty_scraped_data(),
            "page_type": "article",
            "status": "error",
            "error": (
                f"Failed to download page: "
                f"{type(e).__name__}: {e}"
            ),
        }

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Trafilatura
    # ---------------------------------------------------------

    trafilatura_data = extract_with_trafilatura(
        html,
        url,
    )

    # ---------------------------------------------------------
    # Newspaper4k
    # ---------------------------------------------------------

    newspaper_data = extract_with_newspaper(
        url,
    )

    # ---------------------------------------------------------
    # Basic HTML data
    # ---------------------------------------------------------

    html_title = extract_title_from_html(
        soup
    )

    standfirst = extract_standfirst(
        soup
    )

    html_images = extract_images_from_html(
        soup,
        url,
    )

    html_videos = extract_videos_from_html(
        soup,
        url,
    )

    # ---------------------------------------------------------
    # Select best available values
    #
    # For this test we intentionally prefer:
    # Trafilatura -> Newspaper4k -> HTML
    #
    # We will NOT make a final decision about the best
    # extractor until we inspect E0 output.
    # ---------------------------------------------------------

    title = (
        trafilatura_data["title"]
        or newspaper_data["title"]
        or html_title
    )

    text = (
        trafilatura_data["text"]
        or newspaper_data["text"]
    )

    author = (
        trafilatura_data["author"]
        or newspaper_data["author"]
    )

    published_at = (
        trafilatura_data["published_at"]
        or newspaper_data["published_at"]
    )

    main_image = (
        newspaper_data["main_image"]
        or (
            html_images[0]
            if html_images
            else ""
        )
    )

    images = []

    for image in (
        newspaper_data["images"]
        + html_images
    ):
        if image and image not in images:
            images.append(image)

    videos = []

    for video in (
        newspaper_data["videos"]
        + html_videos
    ):
        if video and video not in videos:
            videos.append(video)

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if not text or len(text.strip()) < 100:
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
            "page_type": "article",
            "status": "error",
            "error": (
                "Article text could not be extracted "
                "or is too short."
            ),
        }

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
        "page_type": "article",
        "status": "success",
        "error": "",
    }
