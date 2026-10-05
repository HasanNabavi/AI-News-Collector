import json
import re
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


INPUT_FILE = "C1_NewsAfterLinkEquivalencyRun.json"
OUTPUT_FILE = "A1_Test_MediaExtractor.json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def load_news():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    return data.get("news", [])


def absolute_url(url, base_url):
    if not url:
        return ""

    return urljoin(
        base_url,
        url
    )


def get_attribute_values(tag):
    """
    Collect potentially useful media-related attributes
    from an HTML tag.
    """

    attributes = {}

    interesting_attributes = [
        "src",
        "srcset",
        "poster",
        "data-src",
        "data-srcset",
        "data-lazy-src",
        "data-original",
        "data-playable",
        "data-media-vpid",
        "data-media-meta",
        "data-media",
        "data-video",
        "data-video-id",
        "data-vpid",
    ]

    for attribute in interesting_attributes:

        if tag.has_attr(attribute):

            value = tag.get(attribute)

            if value:
                attributes[attribute] = value

    return attributes


def inspect_figures(soup, page_url):
    """
    Inspect all <figure> elements.

    This remains useful for identifying article-owned
    images and embedded media.
    """

    images = []
    videos = []
    video_posters = []

    figure_results = []

    figures = soup.find_all("figure")

    for number, figure in enumerate(
        figures,
        start=1
    ):

        figure_images = []
        figure_videos = []
        figure_posters = []

        details = {}

        # -------------------------------------------------
        # Images
        # -------------------------------------------------

        image_tags = figure.find_all("img")

        for image in image_tags:

            image_url = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-lazy-src")
                or image.get("data-original")
            )

            if image_url:

                image_url = absolute_url(
                    image_url,
                    page_url
                )

                if image_url not in figure_images:
                    figure_images.append(image_url)

                if image_url not in images:
                    images.append(image_url)

                details["image"] = {
                    "url": image_url,
                    "alt": image.get(
                        "alt",
                        ""
                    ),
                    "caption": (
                        figure.find(
                            "figcaption"
                        ).get_text(
                            " ",
                            strip=True
                        )
                        if figure.find("figcaption")
                        else ""
                    )
                }

        # -------------------------------------------------
        # Video elements
        # -------------------------------------------------

        video_tags = figure.find_all("video")

        for video in video_tags:

            poster = video.get("poster")

            if poster:

                poster = absolute_url(
                    poster,
                    page_url
                )

                if poster not in figure_posters:
                    figure_posters.append(poster)

                if poster not in video_posters:
                    video_posters.append(poster)

            video_src = video.get("src")

            if video_src:

                video_src = absolute_url(
                    video_src,
                    page_url
                )

                if video_src not in figure_videos:
                    figure_videos.append(video_src)

                if video_src not in videos:
                    videos.append(video_src)

            for source in video.find_all("source"):

                source_url = source.get("src")

                if source_url:

                    source_url = absolute_url(
                        source_url,
                        page_url
                    )

                    if source_url not in figure_videos:
                        figure_videos.append(
                            source_url
                        )

                    if source_url not in videos:
                        videos.append(
                            source_url
                        )

        # -------------------------------------------------
        # Iframes
        # -------------------------------------------------

        iframe_tags = figure.find_all("iframe")

        iframe_urls = []

        for iframe in iframe_tags:

            iframe_url = iframe.get("src")

            if iframe_url:

                iframe_url = absolute_url(
                    iframe_url,
                    page_url
                )

                iframe_urls.append(
                    iframe_url
                )

        if iframe_urls:
            details["iframes"] = iframe_urls

        # -------------------------------------------------
        # Store figure result
        # -------------------------------------------------

        figure_results.append(
            {
                "figure_number": number,
                "images": figure_images,
                "videos": figure_videos,
                "video_posters": figure_posters,
                "details": details
            }
        )

    return (
        images,
        videos,
        video_posters,
        figure_results
    )


def inspect_global_media(soup, page_url):
    """
    Inspect media elements across the entire document,
    not only inside <figure>.

    This is diagnostic only.
    """

    result = {
        "videos": [],
        "sources": [],
        "iframes": [],
        "video_posters": [],
        "media_attributes": []
    }

    # -----------------------------------------------------
    # All <video>
    # -----------------------------------------------------

    for video in soup.find_all("video"):

        video_info = {
            "tag": "video",
            "attributes": get_attribute_values(video),
            "sources": []
        }

        video_src = video.get("src")

        if video_src:
            video_info["src_absolute"] = absolute_url(
                video_src,
                page_url
            )

        poster = video.get("poster")

        if poster:
            video_info["poster_absolute"] = absolute_url(
                poster,
                page_url
            )

            result["video_posters"].append(
                video_info["poster_absolute"]
            )

        for source in video.find_all("source"):

            source_url = source.get("src")

            if source_url:

                source_absolute = absolute_url(
                    source_url,
                    page_url
                )

                video_info["sources"].append(
                    {
                        "url": source_absolute,
                        "type": source.get(
                            "type",
                            ""
                        )
                    }
                )

                result["sources"].append(
                    source_absolute
                )

        result["videos"].append(
            video_info
        )

    # -----------------------------------------------------
    # All <iframe>
    # -----------------------------------------------------

    for iframe in soup.find_all("iframe"):

        iframe_url = iframe.get("src")

        if not iframe_url:
            continue

        result["iframes"].append(
            {
                "url": absolute_url(
                    iframe_url,
                    page_url
                ),
                "attributes": get_attribute_values(
                    iframe
                )
            }
        )

    # -----------------------------------------------------
    # Elements containing BBC media attributes
    # -----------------------------------------------------

    media_attribute_names = [
        "data-playable",
        "data-media-vpid",
        "data-media-meta",
        "data-media",
        "data-video",
        "data-video-id",
        "data-vpid"
    ]

    for tag in soup.find_all(True):

        found_attributes = {}

        for attribute in media_attribute_names:

            if tag.has_attr(attribute):

                value = tag.get(attribute)

                if value:
                    found_attributes[attribute] = value

        if found_attributes:

            result["media_attributes"].append(
                {
                    "tag": tag.name,
                    "attributes": found_attributes
                }
            )

    # Remove duplicates from simple lists.

    result["video_posters"] = list(
        dict.fromkeys(
            result["video_posters"]
        )
    )

    result["sources"] = list(
        dict.fromkeys(
            result["sources"]
        )
    )

    return result


def inspect_scripts(soup):
    """
    Search JavaScript blocks for BBC/video-related
    keywords.

    We do not attempt to interpret the data yet.
    The purpose is to discover how BBC exposes
    player metadata in the current HTML.
    """

    keywords = [
        "media-vpid",
        "vpid",
        "mediaMeta",
        "media-meta",
        "playable",
        "video",
        "playlist",
        "mediator",
        "bbcmedia"
    ]

    matches = []

    for number, script in enumerate(
        soup.find_all("script"),
        start=1
    ):

        script_text = script.string

        if not script_text:
            script_text = script.get_text()

        if not script_text:
            continue

        matched_keywords = []

        lower_text = script_text.lower()

        for keyword in keywords:

            if keyword.lower() in lower_text:

                matched_keywords.append(
                    keyword
                )

        if not matched_keywords:
            continue

        # Keep only a limited diagnostic preview.
        preview_length = 3000

        matches.append(
            {
                "script_number": number,
                "matched_keywords": (
                    matched_keywords
                ),
                "length": len(script_text),
                "preview": script_text[
                    :preview_length
                ]
            }
        )

    return matches


def inspect_article(url):
    """
    Download one BBC page and perform diagnostic
    media inspection.
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    (
        figure_images,
        figure_videos,
        figure_posters,
        figure_results
    ) = inspect_figures(
        soup,
        url
    )

    global_media = inspect_global_media(
        soup,
        url
    )

    script_matches = inspect_scripts(
        soup
    )

    return {
        "status": "success",
        "error": "",

        "images": figure_images,

        "videos": figure_videos,

        "video_posters": figure_posters,

        "figure_results": figure_results,

        "global_media": global_media,

        "script_matches": script_matches
    }


def run_test():

    news = load_news()

    print(
        "BBC Media Extraction Test"
    )
    print(
        "=" * 40
    )

    results = []

    successful = 0
    errors = 0

    for index, news_item in enumerate(
        news,
        start=1
    ):

        title = news_item.get(
            "title",
            "No title"
        )

        url = news_item.get(
            "url",
            ""
        )

        print()
        print(
            f"[{index}/{len(news)}]"
        )
        print(
            f"Title: {title}"
        )
        print(
            f"URL: {url}"
        )

        result = {
            "title": title,
            "url": url,
            "status": "success",
            "error": "",
            "images": [],
            "videos": [],
            "video_posters": [],
            "figure_results": [],
            "global_media": {},
            "script_matches": []
        }

        try:

            inspection = inspect_article(
                url
            )

            result.update(
                inspection
            )

            successful += 1

            print(
                "Status: success"
            )

            print(
                "Figure images: "
                f"{len(result['images'])}"
            )

            print(
                "Global videos: "
                f"{len(result['global_media'].get('videos', []))}"
            )

            print(
                "Global iframes: "
                f"{len(result['global_media'].get('iframes', []))}"
            )

            print(
                "Media attributes: "
                f"{len(result['global_media'].get('media_attributes', []))}"
            )

            print(
                "Matching scripts: "
                f"{len(result['script_matches'])}"
            )

        except Exception as error:

            result["status"] = "error"

            result["error"] = (
                f"{type(error).__name__}: "
                f"{error}"
            )

            errors += 1

            print(
                "Status: error"
            )

            print(
                f"Error: {result['error']}"
            )

        results.append(
            result
        )

    output = {
        "test_summary": {
            "input_news": len(news),
            "successful": successful,
            "errors": errors
        },
        "news": results
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        "=" * 40
    )
    print(
        f"Input news: {len(news)}"
    )
    print(
        f"Successful: {successful}"
    )
    print(
        f"Errors: {errors}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    run_test()
