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


def is_article_url(url):
    return "/news/articles/" in url.lower()


def empty_scraped_data():
    return {
        "text": "",
        "main_image": "",
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


def extract_with_trafilatura(html):
    result = {
        "text": "",
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
        )

        if metadata:
            data = metadata.as_dict()

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
        "text": "",
        "main_image": "",
        "videos": [],
    }

    try:
        article = newspaper.article(
            url,
            language="en",
        )

        result["text"] = (
            article.text or ""
        ).strip()

        result["main_image"] = (
            article.top_image or ""
        ).strip()

        result["videos"] = list(
            article.movies or []
        )

    except Exception:
        pass

    return result


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

    # ---------------------------------------------------------
    # Page type detection
    # ---------------------------------------------------------

    if not url:
        return None

    if not is_article_url(url):
        return None

    # ---------------------------------------------------------
    # Download article page
    # ---------------------------------------------------------

    try:
        html = get_html(url)

    except Exception:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Trafilatura
    # ---------------------------------------------------------

    trafilatura_data = extract_with_trafilatura(
        html
    )

    # ---------------------------------------------------------
    # Newspaper4k
    # ---------------------------------------------------------

    newspaper_data = extract_with_newspaper(
        url
    )

    # ---------------------------------------------------------
    # Basic HTML data
    # ---------------------------------------------------------

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
    # Text:
    # Trafilatura -> Newspaper4k
    #
    # Main image:
    # Newspaper4k -> HTML
    #
    # Videos:
    # Newspaper4k + HTML
    # ---------------------------------------------------------

    text = (
        trafilatura_data["text"]
        or newspaper_data["text"]
    )

    main_image = (
        newspaper_data["main_image"]
        or (
            html_images[0]
            if html_images
            else ""
        )
    )

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
        return None

    # ---------------------------------------------------------
    # Final scraped data
    # ---------------------------------------------------------

    return {
        "text": text,
        "main_image": main_image,
        "videos": videos,
    }
