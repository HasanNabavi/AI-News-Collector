import json
import requests
from bs4 import BeautifulSoup
import yt_dlp


INPUT_FILE = "C1_NewsAfterLinkEquivalencyRun.json"
OUTPUT_FILE = "A1_Test_MediaExtractor.json"


def extract_html_media(html):
    soup = BeautifulSoup(html, "html.parser")

    figure_results = []

    for figure in soup.find_all("figure"):

        images = []

        for img in figure.find_all("img"):

            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            if src:
                images.append({
                    "url": src,
                    "alt": img.get("alt", "")
                })

        videos = []

        for video in figure.find_all("video"):

            src = video.get("src")

            if src:
                videos.append({
                    "url": src,
                    "poster": video.get("poster", "")
                })

            for source in video.find_all("source"):

                source_src = source.get("src")

                if source_src:
                    videos.append({
                        "url": source_src,
                        "poster": video.get("poster", "")
                    })

        if images or videos:

            figure_results.append({
                "images": images,
                "videos": videos
            })

    global_media = {
        "videos": [],
        "video_posters": [],
        "iframes": [],
        "media_attributes": [],
        "sources": []
    }

    for video in soup.find_all("video"):

        src = video.get("src")

        if src:
            global_media["videos"].append(src)

        poster = video.get("poster")

        if poster:
            global_media["video_posters"].append(poster)

    for iframe in soup.find_all("iframe"):

        src = iframe.get("src")

        if src:
            global_media["iframes"].append(src)

    media_attributes = [
        "data-playable",
        "data-media-vpid",
        "data-media-meta",
        "data-media",
        "data-video",
        "data-video-id",
        "data-vpid"
    ]

    for tag in soup.find_all(True):

        for attribute in media_attributes:

            value = tag.get(attribute)

            if value:

                global_media["media_attributes"].append({
                    "attribute": attribute,
                    "value": value
                })

    for source in soup.find_all("source"):

        src = source.get("src")

        if src:
            global_media["sources"].append(src)

    return {
        "figure_results": figure_results,
        "global_media": global_media
    }


def extract_yt_dlp(url):

    result = {
        "success": False,
        "entry_count": 0,
        "video_count": 0,
        "entries": [],
        "videos": [],
        "error": None
    }

    try:

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False
        }

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        if not info:

            result["success"] = True
            return result

        entries = info.get("entries")

        if entries is None:

            entries = [info]

        else:

            entries = [
                entry
                for entry in entries
                if entry
            ]

        result["entry_count"] = len(entries)

        for entry in entries:

            entry_data = {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "url": entry.get("url"),
                "webpage_url": entry.get("webpage_url"),
                "duration": entry.get("duration"),
                "ext": entry.get("ext")
            }

            result["entries"].append(
                entry_data
            )

            if entry.get("url"):

                result["videos"].append(
                    entry_data
                )

        result["video_count"] = len(
            result["videos"]
        )

        result["success"] = True

    except Exception as error:

        result["error"] = str(error)

    return result


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    news = data["news"]

    results = []

    success_count = 0
    error_count = 0

    total_ytdlp_entries = 0
    total_ytdlp_videos = 0

    for index, item in enumerate(
        news,
        start=1
    ):

        url = item.get(
            "url",
            ""
        )

        print()
        print(
            f"[{index}/{len(news)}] {url}"
        )

        result = {
            "title": item.get("title"),
            "source": item.get("source"),
            "url": url,
            "html_media": None,
            "yt_dlp": None,
            "error": None
        }

        try:

            response = requests.get(
                url,
                timeout=30,
                headers={
                    "User-Agent":
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                }
            )

            response.raise_for_status()

            result["html_media"] = (
                extract_html_media(
                    response.text
                )
            )

            if (
                "bbc.com/news/articles/" in url
                or
                "bbc.co.uk/news/articles/" in url
            ):

                print(
                    "Running yt-dlp..."
                )

                result["yt_dlp"] = (
                    extract_yt_dlp(url)
                )

                if result["yt_dlp"]["success"]:

                    entry_count = (
                        result["yt_dlp"]
                        ["entry_count"]
                    )

                    video_count = (
                        result["yt_dlp"]
                        ["video_count"]
                    )

                    total_ytdlp_entries += (
                        entry_count
                    )

                    total_ytdlp_videos += (
                        video_count
                    )

                    print(
                        "yt-dlp entries:",
                        entry_count
                    )

                    print(
                        "yt-dlp videos:",
                        video_count
                    )

                else:

                    print(
                        "yt-dlp error:",
                        result["yt_dlp"]
                        ["error"]
                    )

            success_count += 1

        except Exception as error:

            result["error"] = str(error)

            error_count += 1

        results.append(result)

    output = {
        "test_summary": {
            "input_news": len(news),
            "successful": success_count,
            "errors": error_count,
            "yt_dlp_total_entries": (
                total_ytdlp_entries
            ),
            "yt_dlp_total_videos": (
                total_ytdlp_videos
            )
        },
        "results": results
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
    print("=" * 40)
    print("Test completed")
    print(
        f"Input news: {len(news)}"
    )
    print(
        f"Successful: {success_count}"
    )
    print(
        f"Errors: {error_count}"
    )
    print(
        "yt-dlp total entries:",
        total_ytdlp_entries
    )
    print(
        "yt-dlp total videos:",
        total_ytdlp_videos
    )
    print("=" * 40)


if __name__ == "__main__":
    main()
