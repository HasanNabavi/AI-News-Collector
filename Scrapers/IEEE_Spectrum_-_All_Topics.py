import json
import requests
import trafilatura
import newspaper
import yt_dlp

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


def empty_scraped_data():
    return {
        "text": "",
        "main_image": None,
        "videos": []
    }


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def is_article_url(url):
    parsed = urlparse(url)

    if parsed.netloc != "spectrum.ieee.org":
        return False

    excluded_paths = [
        "/tag/",
        "/topic/",
        "/author/",
        "/search",
        "/newsletter"
    ]

    for path in excluded_paths:
        if parsed.path.startswith(path):
            return False

    return True


def extract_article_text(soup):
    """
    Extract the actual article body from IEEE Spectrum.

    The article content is contained inside:
        div.body-description

    Related content starts at:
        div.around-the-web

    Therefore, we keep all direct article elements before
    the around-the-web block.

    Article headings (h2/h3) are valid article content and
    must NOT be treated as the end of the article.
    """

    body_description = soup.select_one(
        "div.body.js-listicle-body div.body-description"
    )

    if not body_description:
        return ""

    content_parts = []

    for element in body_description.find_all(
        recursive=False
    ):

        # Related content starts here.
        if (
            element.name == "div"
            and "around-the-web" in (
                element.get("class") or []
            )
        ):
            break

        # Ignore empty advertising placeholders.
        if element.name == "p":
            if element.select_one(
                ".rblad-ieee_in_content"
            ):
                text = element.get_text(
                    " ",
                    strip=True
                )

                if not text:
                    continue

            text = element.get_text(
                " ",
                strip=True
            )

            if text:
                content_parts.append(text)

        # Article section headings are part of the article.
        elif element.name in ["h2", "h3"]:
            text = element.get_text(
                " ",
                strip=True
            )

            if text:
                content_parts.append(text)

    return "\n\n".join(
        content_parts
    ).strip()


def extract_with_trafilatura(html):
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True
        )

        return text.strip() if text else ""

    except Exception:
        return ""


def extract_with_newspaper(url):
    try:
        article = newspaper.article(url)

        text = article.text.strip()

        return text

    except Exception:
        return ""


def extract_main_image(soup):
    # IEEE Spectrum's actual hero image.
    hero_image = soup.select_one(
        "img.rm-lazyloadable-image.rm-hero-media"
    )

    if hero_image:
        src = (
            hero_image.get("src")
            or hero_image.get("data-src")
            or hero_image.get("data-original")
        )

        if src:
            return urljoin(
                "https://spectrum.ieee.org/",
                src
            )

    # Fallback 1: Open Graph image.
    og_image = soup.find(
        "meta",
        property="og:image"
    )

    if og_image and og_image.get("content"):
        return urljoin(
            "https://spectrum.ieee.org/",
            og_image["content"]
        )

    # Fallback 2: Twitter image.
    twitter_image = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        }
    )

    if twitter_image and twitter_image.get("content"):
        return urljoin(
            "https://spectrum.ieee.org/",
            twitter_image["content"]
        )

    # Fallback 3: JSON-LD.
    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )

            if isinstance(data, dict):
                image = data.get("image")

                if isinstance(image, str):
                    return urljoin(
                        "https://spectrum.ieee.org/",
                        image
                    )

                if isinstance(image, list) and image:
                    return urljoin(
                        "https://spectrum.ieee.org/",
                        image[0]
                    )

                if isinstance(image, dict):
                    image_url = image.get("url")

                    if image_url:
                        return urljoin(
                            "https://spectrum.ieee.org/",
                            image_url
                        )

        except Exception:
            continue

    return None


def extract_videos_from_html(soup):
    videos = []

    # Real YouTube embeds only.
    for iframe in soup.find_all("iframe"):

        src = iframe.get("src")

        if not src:
            continue

        parsed = urlparse(src)
        hostname = parsed.netloc.lower()

        if (
            "youtube.com" in hostname
            or "youtube-nocookie.com" in hostname
            or "youtu.be" in hostname
        ):
            video_url = urljoin(
                "https://spectrum.ieee.org/",
                src
            )

            if video_url not in videos:
                videos.append(video_url)

    # HTML5 video elements.
    for video in soup.find_all("video"):

        src = video.get("src")

        if src:
            video_url = urljoin(
                "https://spectrum.ieee.org/",
                src
            )

            if video_url not in videos:
                videos.append(video_url)

        for source in video.find_all("source"):

            src = source.get("src")

            if not src:
                continue

            video_url = urljoin(
                "https://spectrum.ieee.org/",
                src
            )

            if video_url not in videos:
                videos.append(video_url)

    return videos


def extract_videos_with_yt_dlp(url):
    videos = []

    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                url,
                download=False
            )

        if not info:
            return videos

        webpage_url = info.get("webpage_url")

        if webpage_url:
            videos.append(webpage_url)

    except Exception:
        pass

    return videos


def scrape(url):

    result = empty_scraped_data()

    if not is_article_url(url):
        return result

    try:
        html = get_html(url)

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # --------------------------------------------------
        # ARTICLE TEXT
        # --------------------------------------------------

        text = extract_article_text(soup)

        # Fallback only if the dedicated IEEE extraction
        # fails completely.
        if not text:
            text = extract_with_trafilatura(
                html
            )

        if not text:
            text = extract_with_newspaper(
                url
            )

        # --------------------------------------------------
        # MAIN IMAGE
        # --------------------------------------------------

        main_image = extract_main_image(
            soup
        )

        # --------------------------------------------------
        # VIDEOS
        # --------------------------------------------------

        videos = extract_videos_from_html(
            soup
        )

        if not videos:
            videos = extract_videos_with_yt_dlp(
                url
            )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------

        if not text or len(text.strip()) < 100:
            return {
                "text": "",
                "main_image": main_image,
                "videos": videos
            }

        result = {
            "text": text.strip(),
            "main_image": main_image,
            "videos": videos
        }

        return result

    except Exception:
        return result
