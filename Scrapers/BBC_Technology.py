import requests
import trafilatura
import newspaper
import yt_dlp

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


def extract_videos_with_yt_dlp(url):
    videos = []

    try:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                url,
                download=False,
            )

        if not info:
            return videos

        entries = info.get("entries")

        if entries is None:
            entries = [info]

        for entry in entries:
            if not entry:
                continue

            video_url = entry.get("url")

            if (
                video_url
                and video_url not in videos
            ):
                videos.append(video_url)

    except Exception:
        pass

    return videos


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
    #
    # Any download failure is a real scraping error.
    # Let the exception propagate to E0.
    # ---------------------------------------------------------

    html = get_html(url)

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

    # ---------------------------------------------------------
    # YouTube-DL / yt-dlp
    #
    # Extract actual embedded BBC video streams.
    # Only the video URLs are stored.
    # ---------------------------------------------------------

    videos = extract_videos_with_yt_dlp(
        url
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
    # yt-dlp
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

    # ---------------------------------------------------------
    # Validation
    #
    # Article was identified correctly, but its content
    # could not be extracted sufficiently.
    # This is a real scraping error, not a skip.
    # ---------------------------------------------------------

    if not text or len(text.strip()) < 100:
        raise RuntimeError(
            "Article text could not be extracted "
            "or is too short."
        )

    # ---------------------------------------------------------
    # Final scraped data
    # ---------------------------------------------------------

    return {
        "text": text,
        "main_image": main_image,
        "videos": videos,
    }
