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
    }

    try:
        article = newspaper.article(
            url,
            language="en",
        )

        result["text"] = (
            article.text or ""
        ).strip()

    except Exception:
        pass

    return result


def extract_main_image(soup, url):

    # ---------------------------------------------------------
    # 1. Open Graph image
    # ---------------------------------------------------------

    og_image = soup.find(
        "meta",
        property="og:image",
    )

    if og_image:
        image_url = og_image.get(
            "content"
        )

        if image_url:
            return urljoin(
                url,
                image_url,
            )

    # ---------------------------------------------------------
    # 2. Twitter image
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
                url,
                image_url,
            )

    # ---------------------------------------------------------
    # 3. JSON-LD image
    # ---------------------------------------------------------

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):

        try:
            data = json.loads(
                script.string
                or script.get_text()
            )

        except Exception:
            continue

        objects = []

        if isinstance(data, dict):

            objects.append(data)

            graph = data.get(
                "@graph"
            )

            if isinstance(
                graph,
                list,
            ):
                objects.extend(
                    graph
                )

        elif isinstance(
            data,
            list,
        ):
            objects.extend(
                data
            )

        for item in objects:

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
                    url,
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
                        url,
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
                            url,
                            image_item,
                        )

                    if isinstance(
                        image_item,
                        dict,
                    ):

                        image_url = (
                            image_item.get(
                                "url"
                            )
                        )

                        if image_url:
                            return urljoin(
                                url,
                                image_url,
                            )

    # ---------------------------------------------------------
    # 4. First image inside <figure>
    # ---------------------------------------------------------

    figure = soup.find(
        "figure"
    )

    if figure:

        img = figure.find(
            "img"
        )

        if img:

            for attribute in [
                "src",
                "data-src",
                "data-lazy-src",
                "data-original",
            ]:

                image_url = img.get(
                    attribute
                )

                if image_url:
                    return urljoin(
                        url,
                        image_url,
                    )

            srcset = img.get(
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
                        url,
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

    html = get_html(
        url
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # ---------------------------------------------------------
    # Trafilatura
    # ---------------------------------------------------------

    trafilatura_data = (
        extract_with_trafilatura(
            html
        )
    )

    # ---------------------------------------------------------
    # Newspaper4k
    # ---------------------------------------------------------

    newspaper_data = (
        extract_with_newspaper(
            url
        )
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

    videos = extract_videos_with_yt_dlp(
        url
    )

    # ---------------------------------------------------------
    # Select best available text
    # ---------------------------------------------------------

    text = (
        trafilatura_data["text"]
        or newspaper_data["text"]
    )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    if not text or len(
        text.strip()
    ) < 100:

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
