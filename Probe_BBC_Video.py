import json
import re
import requests
from bs4 import BeautifulSoup


URLS = [
    "https://www.bbc.co.uk/news/articles/c6y9z9r4ejzwo",
    "https://www.bbc.co.uk/news/articles/c6eq84eygz0qo",
]

OUTPUT_FILE = "Probe_BBC_Video_Output.json"


def inspect_page(url):

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        "url": url,
        "status": response.status_code,
        "counts": {},
        "video_components": [],
        "media_urls": [],
        "script_keywords": []
    }

    # --------------------------------
    # Count basic media elements
    # --------------------------------

    result["counts"] = {
        "video": len(soup.find_all("video")),
        "source": len(soup.find_all("source")),
        "iframe": len(soup.find_all("iframe")),
        "audio": len(soup.find_all("audio")),
        "object": len(soup.find_all("object")),
        "embed": len(soup.find_all("embed")),
    }

    # --------------------------------
    # Find only component/testid names
    # --------------------------------

    seen = set()

    for element in soup.find_all(True):

        attrs = element.attrs

        for key in ["data-component", "data-testid"]:

            value = attrs.get(key)

            if not value:
                continue

            if re.search(
                r"video|media|player",
                str(value),
                re.IGNORECASE
            ):

                item = f"{key}={value}"

                if item not in seen:
                    seen.add(item)
                    result["video_components"].append(item)

    # --------------------------------
    # Find media URLs only
    # --------------------------------

    urls = set()

    for element in soup.find_all(True):

        for value in element.attrs.values():

            if isinstance(value, list):
                values = value
            else:
                values = [value]

            for value in values:

                if not isinstance(value, str):
                    continue

                found = re.findall(
                    r'https?://[^"\'>\s]+',
                    value
                )

                for url_found in found:

                    if re.search(
                        r"(\.mp4|\.m3u8|video|media)",
                        url_found,
                        re.IGNORECASE
                    ):
                        urls.add(url_found)

    result["media_urls"] = sorted(urls)

    # --------------------------------
    # Find scripts containing keywords
    # --------------------------------

    keywords = set()

    for script in soup.find_all("script"):

        text = script.string or script.get_text()

        if not text:
            continue

        found = re.findall(
            r"\b(video|media|player|playlist|m3u8|mp4|manifest)\b",
            text,
            re.IGNORECASE
        )

        keywords.update(
            word.lower() for word in found
        )

    result["script_keywords"] = sorted(keywords)

    return result


def main():

    results = []

    for url in URLS:

        try:
            results.append(
                inspect_page(url)
            )

        except Exception as error:

            results.append({
                "url": url,
                "error": str(error)
            })

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Probe completed.")


if __name__ == "__main__":
    main()
