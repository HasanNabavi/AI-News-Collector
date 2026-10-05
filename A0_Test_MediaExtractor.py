import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


INPUT_FILE = "C1_NewsAfterLinkEquivalencyRun.json"
OUTPUT_FILE = "A1_Test_MediaExtractor.json"

REQUEST_TIMEOUT = 30

SCRIPT_KEYWORDS = [
    "data-media-vpid",
    "media-vpid",
    "mediaMeta",
    "media-meta",
    "data-playable",
    "bbcmedia",
    "vpid",
]


def load_news():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    return data.get("news", [])


def fetch_page(url):
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        }
    )

    response.raise_for_status()

    return response.text


def clean_url(url, base_url):
    if not url:
        return ""

    return urljoin(
        base_url,
        url.strip()
    )


def extract_figure_results(soup, page_url):
    results = []

    figures = soup.find_all("figure")

    for figure_number, figure in enumerate(
        figures,
        start=1
    ):
        images = []

        for image in figure.find_all("img"):
            src = (
                image.get("src")
                or image.get("data-src")
                or image.get("data-original")
                or ""
            )

            if src:
                images.append({
                    "url": clean_url(
                        src,
                        page_url
                    ),
                    "alt": image.get(
                        "alt",
                        ""
                    )
                })

        videos = []

        for video in figure.find_all("video"):
            video_data = {
                "src": clean_url(
                    video.get("src", ""),
                    page_url
                ),
                "poster": clean_url(
                    video.get("poster", ""),
                    page_url
                )
            }

            sources = []

            for source in video.find_all("source"):
                source_url = source.get(
                    "src",
                    ""
                )

                if source_url:
                    sources.append(
                        clean_url(
                            source_url,
                            page_url
                        )
                    )

            if sources:
                video_data["sources"] = sources

            videos.append(video_data)

        if images or videos:
            result = {
                "figure_number": figure_number
            }

            if images:
                result["images"] = images

            if videos:
                result["videos"] = videos

            results.append(result)

    return results


def extract_global_videos(soup, page_url):
    videos = []

    for video_number, video in enumerate(
        soup.find_all("video"),
        start=1
    ):
        result = {
            "video_number": video_number
        }

        src = video.get("src", "")

        if src:
            result["src"] = clean_url(
                src,
                page_url
            )

        poster = video.get(
            "poster",
            ""
        )

        if poster:
            result["poster"] = clean_url(
                poster,
                page_url
            )

        sources = []

        for source in video.find_all("source"):
            source_url = source.get(
                "src",
                ""
            )

            if source_url:
                sources.append(
                    clean_url(
                        source_url,
                        page_url
                    )
                )

        if sources:
            result["sources"] = sources

        videos.append(result)

    return videos


def extract_iframes(soup, page_url):
    iframes = []

    for iframe in soup.find_all("iframe"):
        src = iframe.get(
            "src",
            ""
        )

        if not src:
            continue

        iframes.append(
            clean_url(
                src,
                page_url
            )
        )

    return list(
        dict.fromkeys(iframes)
    )


def extract_video_posters(soup, page_url):
    posters = []

    for video in soup.find_all("video"):
        poster = video.get(
            "poster",
            ""
        )

        if poster:
            posters.append(
                clean_url(
                    poster,
                    page_url
                )
            )

    return list(
        dict.fromkeys(posters)
    )


def extract_media_attributes(soup, page_url):
    results = []

    relevant_attributes = [
        "data-playable",
        "data-media-vpid",
        "data-media-meta",
        "data-media",
        "data-video",
        "data-video-id",
        "data-vpid",
    ]

    for tag in soup.find_all(True):

        found_attributes = {}

        for attribute in relevant_attributes:
            if attribute not in tag.attrs:
                continue

            value = tag.get(
                attribute
            )

            if isinstance(value, list):
                value = " ".join(value)

            value = str(value).strip()

            if not value:
                continue

            # Keep diagnostic output compact.
            if len(value) > 500:
                value = value[:500] + "..."

            found_attributes[attribute] = value

        if found_attributes:
            result = {
                "tag": tag.name,
                "attributes": found_attributes
            }

            results.append(result)

    return results


def extract_script_matches(soup):
    results = []

    scripts = soup.find_all("script")

    for script_number, script in enumerate(
        scripts,
        start=1
    ):
        content = script.string

        if not content:
            content = script.get_text(
                strip=False
            )

        if not content:
            continue

        matched_keywords = []

        for keyword in SCRIPT_KEYWORDS:
            if keyword.lower() in content.lower():
                matched_keywords.append(
                    keyword
                )

        if matched_keywords:
            results.append({
                "script_number": script_number,
                "matched_keywords": matched_keywords
            })

    return results


def extract_source_tags(soup, page_url):
    sources = []

    for source in soup.find_all("source"):
        src = source.get(
            "src",
            ""
        )

        if not src:
            continue

        source_data = {
            "url": clean_url(
                src,
                page_url
            )
        }

        media = source.get(
            "media",
            ""
        )

        if media:
            source_data["media"] = media

        source_type = source.get(
            "type",
            ""
        )

        if source_type:
            source_data["type"] = source_type

        sources.append(
            source_data
        )

    return sources


def extract_media(page_url, html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    result = {
        "figure_results": extract_figure_results(
            soup,
            page_url
        ),
        "global_media": {
            "videos": extract_global_videos(
                soup,
                page_url
            ),
            "video_posters": extract_video_posters(
                soup,
                page_url
            ),
            "iframes": extract_iframes(
                soup,
                page_url
            ),
            "media_attributes": extract_media_attributes(
                soup,
                page_url
            ),
            "sources": extract_source_tags(
                soup,
                page_url
            ),
        },
        "script_matches": extract_script_matches(
            soup
        )
    }

    return result


def test_news_item(news_item):
    url = news_item.get(
        "url",
        ""
    )

    if not url:
        raise ValueError(
            "URL is empty"
        )

    html = fetch_page(url)

    media_data = extract_media(
        url,
        html
    )

    return media_data


def run_test():
    news = load_news()

    print(
        "BBC / Website Media Extraction Test"
    )
    print(
        "=" * 50
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

        source = news_item.get(
            "source",
            "Unknown source"
        )

        url = news_item.get(
            "url",
            ""
        )

        print()
        print(
            f"[{index}/{len(news)}] {source}"
        )
        print(
            f"Title: {title}"
        )

        try:
            media_data = test_news_item(
                news_item
            )

            result_item = {
                "title": title,
                "source": source,
                "url": url,
                "media_data": media_data
            }

            results.append(
                result_item
            )

            successful += 1

            print(
                "Status: success"
            )

        except Exception as error:
            errors += 1

            results.append({
                "title": title,
                "source": source,
                "url": url,
                "error": (
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            })

            print(
                "Status: error"
            )
            print(
                f"Error: {error}"
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
        "=" * 50
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
    print(
        "Test completed."
    )


if __name__ == "__main__":
    run_test()
