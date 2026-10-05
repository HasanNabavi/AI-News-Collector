import json
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
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
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


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def normalize_url(url, base_url):
    if not url:
        return ""

    return urljoin(
        base_url,
        url
    )


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def extract_media_from_figure(figure, article_url):
    """
    Extract media belonging to one <figure>.
    """

    result = {
        "images": [],
        "videos": [],
        "video_posters": [],
        "details": {}
    }

    # --------------------------------------------------
    # Images
    # --------------------------------------------------

    image = figure.find("img")

    if image:
        image_url = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
            or image.get("data-original")
            or ""
        )

        image_url = normalize_url(
            image_url,
            article_url
        )

        if image_url:
            add_unique(
                result["images"],
                image_url
            )

            figcaption = figure.find(
                "figcaption"
            )

            result["details"]["image"] = {
                "url": image_url,
                "alt": image.get(
                    "alt",
                    ""
                ),
                "caption": (
                    figcaption.get_text(
                        " ",
                        strip=True
                    )
                    if figcaption
                    else ""
                )
            }

    # --------------------------------------------------
    # Video tag
    # --------------------------------------------------

    video = figure.find("video")

    if video:

        video_info = {
            "tag": "video",
            "id": video.get(
                "id",
                ""
            ),
            "title": video.get(
                "data-title",
                ""
            ),
            "duration": video.get(
                "data-duration",
                ""
            ),
            "poster": normalize_url(
                video.get(
                    "poster",
                    ""
                ),
                article_url
            ),
            "sources": []
        }

        if video_info["poster"]:
            add_unique(
                result["video_posters"],
                video_info["poster"]
            )

        video_src = video.get(
            "src",
            ""
        )

        if video_src:
            video_src = normalize_url(
                video_src,
                article_url
            )

            add_unique(
                result["videos"],
                video_src
            )

            video_info["sources"].append(
                video_src
            )

        for source in video.find_all(
            "source"
        ):

            source_url = source.get(
                "src",
                ""
            )

            if not source_url:
                continue

            source_url = normalize_url(
                source_url,
                article_url
            )

            add_unique(
                result["videos"],
                source_url
            )

            video_info["sources"].append(
                source_url
            )

        result["details"]["video"] = (
            video_info
        )

    # --------------------------------------------------
    # iframe
    # --------------------------------------------------

    iframe = figure.find(
        "iframe"
    )

    if iframe:

        iframe_src = iframe.get(
            "src",
            ""
        )

        iframe_src = normalize_url(
            iframe_src,
            article_url
        )

        if iframe_src:

            add_unique(
                result["videos"],
                iframe_src
            )

            result["details"]["iframe"] = {
                "url": iframe_src
            }

    return result


def extract_article_media(
    html,
    article_url
):
    """
    Extract images and videos only
    from <figure> elements.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    images = []
    videos = []
    video_posters = []

    figures = soup.find_all(
        "figure"
    )

    figure_results = []

    for index, figure in enumerate(
        figures,
        start=1
    ):

        media = extract_media_from_figure(
            figure,
            article_url
        )

        if (
            not media["images"]
            and not media["videos"]
            and not media["video_posters"]
        ):
            continue

        for image_url in media["images"]:
            add_unique(
                images,
                image_url
            )

        for video_url in media["videos"]:
            add_unique(
                videos,
                video_url
            )

        for poster_url in media["video_posters"]:
            add_unique(
                video_posters,
                poster_url
            )

        figure_results.append({
            "figure_number": index,
            "images": media["images"],
            "videos": media["videos"],
            "video_posters": media[
                "video_posters"
            ],
            "details": media["details"]
        })

    return {
        "images": images,
        "videos": videos,
        "video_posters": video_posters,
        "figure_results": figure_results
    }


def test_article(
    news_item,
    index,
    total
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
        "=" * 70
    )

    print(
        f"[{index}/{total}] {title}"
    )

    print(
        f"URL: {url}"
    )

    if not url:
        print(
            "ERROR: URL is empty."
        )

        return {
            "title": title,
            "url": url,
            "status": "error",
            "error": "URL is empty.",
            "images": [],
            "videos": [],
            "video_posters": [],
            "figure_results": []
        }

    try:
        html = get_html(
            url
        )

        media = extract_article_media(
            html,
            url
        )

        print(
            "Figures with media: "
            f"{len(media['figure_results'])}"
        )

        print(
            "Article images: "
            f"{len(media['images'])}"
        )

        print(
            "Videos: "
            f"{len(media['videos'])}"
        )

        print(
            "Video posters: "
            f"{len(media['video_posters'])}"
        )

        return {
            "title": title,
            "url": url,
            "status": "success",
            "error": "",
            "images": media["images"],
            "videos": media["videos"],
            "video_posters": media[
                "video_posters"
            ],
            "figure_results": media[
                "figure_results"
            ]
        }

    except Exception as error:

        print(
            "ERROR: "
            f"{type(error).__name__}: {error}"
        )

        return {
            "title": title,
            "url": url,
            "status": "error",
            "error": (
                f"{type(error).__name__}: "
                f"{error}"
            ),
            "images": [],
            "videos": [],
            "video_posters": [],
            "figure_results": []
        }


def main():

    news = load_news()

    print(
        "BBC Test Media Extractor"
    )

    print(
        "=" * 70
    )

    print(
        f"Input news: {len(news)}"
    )

    results = []

    for index, news_item in enumerate(
        news,
        start=1
    ):

        result = test_article(
            news_item,
            index,
            len(news)
        )

        results.append(
            result
        )

    successful = sum(
        1
        for item in results
        if item["status"] == "success"
    )

    errors = sum(
        1
        for item in results
        if item["status"] == "error"
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
        "=" * 70
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
    main()
