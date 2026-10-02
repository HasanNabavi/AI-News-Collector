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
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        "url": url,
        "status_code": response.status_code,
        "video_elements": [],
        "video_attributes": [],
        "video_scripts": []
    }

    # -----------------------------
    # Direct video-related elements
    # -----------------------------

    selectors = [
        "video",
        "source",
        "iframe",
        "[data-component*='video']",
        "[data-testid*='video']",
        "[class*='video']",
        "[id*='video']",
    ]

    seen = set()

    for selector in selectors:

        for element in soup.select(selector):

            attrs = dict(element.attrs)

            key = (
                element.name,
                json.dumps(
                    attrs,
                    sort_keys=True,
                    default=str
                )
            )

            if key in seen:
                continue

            seen.add(key)

            result["video_elements"].append({
                "selector": selector,
                "tag": element.name,
                "attrs": attrs
            })

    # -----------------------------
    # Elements with media-like attrs
    # -----------------------------

    for element in soup.find_all(True):

        attrs = dict(element.attrs)

        attrs_text = json.dumps(
            attrs,
            ensure_ascii=False,
            default=str
        )

        if not re.search(
            r"(video|media|player|playlist|m3u8|mp4)",
            attrs_text,
            re.IGNORECASE
        ):
            continue

        result["video_attributes"].append({
            "tag": element.name,
            "attrs": attrs
        })

    # -----------------------------
    # Scripts containing keywords
    # -----------------------------

    for index, script in enumerate(
        soup.find_all("script")
    ):

        text = script.string or script.get_text()

        if not text:
            continue

        if not re.search(
            r"(video|m3u8|mp4|media|player|playlist)",
            text,
            re.IGNORECASE
        ):
            continue

        # فقط محل وجود keywordها را ثبت کن
        keywords = sorted(
            set(
                re.findall(
                    r"(video|m3u8|mp4|media|player|playlist)",
                    text,
                    re.IGNORECASE
                )
            )
        )

        # URLها را بدون ذخیره کل script استخراج کن
        urls = re.findall(
            r'https?://[^\s"\'<>]+',
            text
        )

        result["video_scripts"].append({
            "script_index": index,
            "type": script.get("type"),
            "keywords": keywords,
            "urls": list(dict.fromkeys(urls))[:20]
        })

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
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
