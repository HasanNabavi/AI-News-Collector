import requests
import trafilatura
import newspaper
import yt_dlp

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json


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
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            include_links=False,
        )

        if text:
            return text.strip()

        result = trafilatura.bare_extraction(
            html,
            include_comments=False,
            include_tables=False,
            include_links=False,
        )

        if result:
            text = result.get("text")

            if text:
                return text.strip()

    except Exception:
        pass

    return ""


def extract_with_newspaper(url):
    try:
        article = newspaper.article(
            url,
            language="en",
        )

        if article and article.text:
            return article.text.strip()

    except Exception:
        pass

    return ""


def extract_main_image(soup, article_url):
    # 1. Open Graph image
    og_image = soup.find(
        "meta",
        attrs={
            "property": "og:image"
        },
    )

    if og_image:
        image_url = og_image.get("content")

        if image_url:
            return urljoin(article_url, image_url)

    # 2. Twitter image
    twitter_image = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        },
    )

    if twitter_image:
        image_url = twitter_image.get("content")

        if image_url:
            return urljoin(article_url, image_url)

    # 3. JSON-LD image
    for script in soup.find_all(
        "script",
        attrs={
            "type": "application/ld+json"
        },
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )

            items = data

            if isinstance(data, dict):
                items = [data]

            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    image = item.get("image")

                    if isinstance(image, str):
                        return urljoin(article_url, image)

                    if isinstance(image, list) and image:
                        if isinstance(image[0], str):
                            return urljoin(
                                article_url,
                                image[0],
                            )

                    if isinstance(image, dict):
                        image_url = image.get("url")

                        if image_url:
                            return urljoin(
                                article_url,
                                image_url,
                            )

        except Exception:
            continue

    # 4. First figure image
    figure = soup.find("figure")

    if figure:
        image = figure.find("img")

        if image:
            image_url = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
            )

            if image_url:
                return urljoin(
                    article_url,
                    image_url,
                )

    return ""


def extract_videos_from_html(soup, article_url):
    videos = []

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")

        if not src:
            src = iframe.get("data-src")

        if not src:
            continue

        video_url = urljoin(
            article_url,
            src,
        )

        parsed = urlparse(video_url)

        host = parsed.netloc.lower()
        path = parsed.path.lower()

        is_youtube_host = host in {
            "youtube.com",
            "www.youtube.com",
            "youtube-nocookie.com",
            "www.youtube-nocookie.com",
        }

        is_youtube_embed = path.startswith("/embed/")

        if is_youtube_host and is_youtube_embed:
            if video_url not in videos:
                videos.append(video_url)

    return videos


def is_article_url(url):
    if not url:
        return False

    parsed = urlparse(url)

    if parsed.netloc.lower() not in {
        "www.therobotreport.com",
        "therobotreport.com",
    }:
        return False

    path = parsed.path.lower()

    excluded_paths = (
        "/category/",
        "/author/",
        "/tag/",
        "/page/",
    )

    if path.startswith(excluded_paths):
        return False

    return True


def scrape(url):
    if not is_article_url(url):
        return None

    html = get_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Text
    # ---------------------------------------------------------

    text = extract_with_trafilatura(html)

    if not text:
        text = extract_with_newspaper(url)

    if not text:
        raise ValueError(
            "Article text could not be extracted."
        )

    # ---------------------------------------------------------
    # Main image
    # ---------------------------------------------------------

    main_image = extract_main_image(
        soup,
        url,
    )

    # ---------------------------------------------------------
    # Videos
    # ---------------------------------------------------------

    videos = extract_videos_from_html(
        soup,
        url,
    )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if len(text.strip()) < 100:
        raise ValueError(
            "Extracted article text is too short."
        )

    return {
        "text": text.strip(),
        "main_image": main_image,
        "videos": videos,
    }
