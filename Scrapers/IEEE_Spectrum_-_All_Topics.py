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


def is_article_url(url):
    if not url:
        return False

    parsed = urlparse(url)

    if parsed.netloc.lower() not in {
        "spectrum.ieee.org",
        "www.spectrum.ieee.org",
    }:
        return False

    path = parsed.path.lower()

    excluded_paths = (
        "/topic/",
        "/tag/",
        "/category/",
        "/search",
        "/author/",
        "/newsletter",
        "/podcasts",
        "/videos",
    )

    if path.startswith(excluded_paths):
        return False

    if path in {"", "/"}:
        return False

    return True


def extract_article_text(soup):
    """
    Extract the actual IEEE Spectrum article body.

    Based on the tested HTML structure:

        div.body.js-listicle-body
            └── div.body-description
                    ├── article content
                    ├── ...
                    ├── first h2
                    └── related/promotional content

    The first h2 marks the beginning of related content.
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

        # -----------------------------------------------------
        # The first H2 marks the beginning of related content.
        # -----------------------------------------------------

        if element.name == "h2":
            break

        # -----------------------------------------------------
        # Keep normal article paragraphs.
        # -----------------------------------------------------

        if element.name == "p":

            text = element.get_text(
                " ",
                strip=True,
            )

            if text:
                content_parts.append(text)

        # -----------------------------------------------------
        # Keep article section headings.
        # -----------------------------------------------------

        elif element.name == "h3":

            text = element.get_text(
                " ",
                strip=True,
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

    # ---------------------------------------------------------
    # 1. IEEE Spectrum hero image
    #
    # Tested structure:
    #
    # img.rm-lazyloadable-image.rm-hero-media
    # ---------------------------------------------------------

    hero_image = soup.select_one(
        "img.rm-lazyloadable-image.rm-hero-media"
    )

    if hero_image:

        image_url = (
            hero_image.get("src")
            or hero_image.get("data-src")
            or hero_image.get("data-lazy-src")
            or hero_image.get("data-original")
        )

        if image_url:
            return urljoin(
                article_url,
                image_url,
            )

        srcset = hero_image.get("srcset")

        if srcset:

            image_url = (
                srcset
                .split(",")[0]
                .strip()
                .split()[0]
            )

            if image_url:
                return urljoin(
                    article_url,
                    image_url,
                )

    # ---------------------------------------------------------
    # 2. Open Graph image
    # ---------------------------------------------------------

    og_image = soup.find(
        "meta",
        attrs={
            "property": "og:image"
        },
    )

    if og_image:

        image_url = og_image.get(
            "content"
        )

        if image_url:
            return urljoin(
                article_url,
                image_url,
            )

    # ---------------------------------------------------------
    # 3. Twitter image
    # ---------------------------------------------------------

    twitter_image = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        },
    )

    if twitter_image:

        image_url = twitter_image.get(
            "content"
        )

        if image_url:
            return urljoin(
                article_url,
                image_url,
            )

    # ---------------------------------------------------------
    # 4. JSON-LD image
    # ---------------------------------------------------------

    for script in soup.find_all(
        "script",
        attrs={
            "type": "application/ld+json"
        },
    ):

        try:
            data = json.loads(
                script.string
                or script.get_text()
            )

        except Exception:
            continue

        items = []

        if isinstance(data, dict):

            items.append(data)

            graph = data.get(
                "@graph"
            )

            if isinstance(graph, list):
                items.extend(graph)

        elif isinstance(data, list):

            items.extend(data)

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            image = item.get(
                "image"
            )

            if isinstance(
                image,
                str,
            ):

                return urljoin(
                    article_url,
                    image,
                )

            if isinstance(
                image,
                dict,
            ):

                image_url = image.get(
                    "url"
                )

                if image_url:
                    return urljoin(
                        article_url,
                        image_url,
                    )

            if isinstance(
                image,
                list,
            ):

                for image_item in image:

                    if isinstance(
                        image_item,
                        str,
                    ):

                        return urljoin(
                            article_url,
                            image_item,
                        )

                    if isinstance(
                        image_item,
                        dict,
                    ):

                        image_url = image_item.get(
                            "url"
                        )

                        if image_url:
                            return urljoin(
                                article_url,
                                image_url,
                            )

    # ---------------------------------------------------------
    # 5. First figure image
    # ---------------------------------------------------------

    figure = soup.find(
        "figure"
    )

    if figure:

        image = figure.find(
            "img"
        )

        if image:

            image_url = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
                or image.get("data-original")
            )

            if image_url:

                return urljoin(
                    article_url,
                    image_url,
                )

            srcset = image.get(
                "srcset"
            )

            if srcset:

                image_url = (
                    srcset
                    .split(",")[0]
                    .strip()
                    .split()[0]
                )

                if image_url:

                    return urljoin(
                        article_url,
                        image_url,
                    )

    return ""


def extract_videos_with_yt_dlp(url):

    videos = []

    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

        if not info:
            return videos

        entries = info.get(
            "entries"
        )

        if entries is None:
            entries = [info]

        for entry in entries:

            if not entry:
                continue

            video_url = entry.get(
                "url"
            )

            if (
                video_url
                and video_url not in videos
            ):

                videos.append(
                    video_url
                )

    except Exception:
        pass

    return videos


def extract_videos_from_html(
    soup,
    article_url,
):

    videos = []

    for iframe in soup.find_all(
        "iframe"
    ):

        src = iframe.get(
            "src"
        )

        if not src:
            src = iframe.get(
                "data-src"
            )

        if not src:
            continue

        video_url = urljoin(
            article_url,
            src,
        )

        parsed = urlparse(
            video_url
        )

        host = parsed.netloc.lower()
        path = parsed.path.lower()

        is_youtube = host in {
            "youtube.com",
            "www.youtube.com",
            "youtube-nocookie.com",
            "www.youtube-nocookie.com",
        }

        is_youtube_embed = path.startswith(
            "/embed/"
        )

        if (
            is_youtube
            and is_youtube_embed
        ):

            if video_url not in videos:
                videos.append(
                    video_url
                )

    return videos


def scrape(url):

    # ---------------------------------------------------------
    # Page type detection
    # ---------------------------------------------------------

    if not is_article_url(url):
        return None

    # ---------------------------------------------------------
    # Download page
    # ---------------------------------------------------------

    html = get_html(
        url
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Text extraction
    #
    # Primary:
    # IEEE Spectrum's actual article HTML structure
    #
    # Fallback:
    # Trafilatura
    #
    # Final fallback:
    # Newspaper4k
    # ---------------------------------------------------------

    text = extract_article_text(
        soup
    )

    if not text:

        text = extract_with_trafilatura(
            html
        )

    if not text:

        text = extract_with_newspaper(
            url
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
    #
    # First try HTML iframe detection.
    # Then try yt-dlp.
    # ---------------------------------------------------------

    videos = extract_videos_from_html(
        soup,
        url,
    )

    yt_dlp_videos = (
        extract_videos_with_yt_dlp(
            url
        )
    )

    for video_url in yt_dlp_videos:

        if video_url not in videos:

            videos.append(
                video_url
            )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if not text:

        raise ValueError(
            "Article text could not be extracted."
        )

    if len(text.strip()) < 100:

        raise ValueError(
            "Extracted article text is too short."
        )

    # ---------------------------------------------------------
    # Final scraped data
    # ---------------------------------------------------------

    return {
        "text": text.strip(),
        "main_image": main_image,
        "videos": videos,
    }
