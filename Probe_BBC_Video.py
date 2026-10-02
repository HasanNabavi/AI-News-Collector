import json
import re
import requests
from bs4 import BeautifulSoup


URLS = [
    "https://www.bbc.co.uk/news/articles/c6y9z9r4ejzwo",
    "https://www.bbc.co.uk/news/articles/c6eq84eygz0qo",
]

OUTPUT_FILE = "Probe_BBC_Video_Output.json"


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_urls(text):
    patterns = [
        r'https?://[^\s"\'<>]+',
        r'//[^\s"\'<>]+'
    ]

    urls = []

    for pattern in patterns:
        urls.extend(re.findall(pattern, text))

    return list(dict.fromkeys(urls))


def inspect_page(url):
    print(f"Inspecting: {url}")

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        },
        timeout=30
    )

    soup = BeautifulSoup(response.text, "html.parser")

    result = {
        "url": url,
        "status_code": response.status_code,
        "html_size": len(response.text),
        "video_elements": [],
        "video_like_elements": [],
        "video_scripts": []
    }

    # --------------------------------------------------
    # 1. Direct video-related elements
    # --------------------------------------------------

    selectors = [
        "video",
        "source",
        "iframe",
        "[data-component*='video']",
        "[data-testid*='video']",
        "[class*='video']",
        "[id*='video']",
    ]

    seen_elements = set()

    for selector in selectors:
        for element in soup.select(selector):

            html = str(element)

            key = html[:3000]

            if key in seen_elements:
                continue

            seen_elements.add(key)

            item = {
                "selector": selector,
                "tag": element.name,
                "attrs": dict(element.attrs),
                "text": clean_text(
                    element.get_text(" ", strip=True)
                )[:500],
                "html": html[:5000],
                "urls": extract_urls(html)
            }

            result["video_elements"].append(item)

    # --------------------------------------------------
    # 2. Any element whose attributes suggest media/video
    # --------------------------------------------------

    for element in soup.find_all(True):

        attrs_text = json.dumps(
            dict(element.attrs),
            ensure_ascii=False,
            default=str
        )

        if not re.search(
            r"(video|media|player|playlist|m3u8|mp4)",
            attrs_text,
            re.IGNORECASE
        ):
            continue

        html = str(element)

        item = {
            "tag": element.name,
            "attrs": dict(element.attrs),
            "text": clean_text(
                element.get_text(" ", strip=True)
            )[:500],
            "html": html[:5000],
            "urls": extract_urls(html)
        }

        result["video_like_elements"].append(item)

    # --------------------------------------------------
    # 3. Scripts containing video/media information
    # --------------------------------------------------

    for index, script in enumerate(soup.find_all("script")):

        script_text = script.string or script.get_text()

        if not script_text:
            continue

        if not re.search(
            r"(video|media|player|playlist|m3u8|mp4|manifest)",
            script_text,
            re.IGNORECASE
        ):
            continue

        matches = []

        for match in re.finditer(
            r"(video|media|player|playlist|m3u8|mp4|manifest)",
            script_text,
            re.IGNORECASE
        ):

            start = max(0, match.start() - 300)
            end = min(len(script_text), match.end() + 1000)

            snippet = script_text[start:end]

            matches.append({
                "keyword": match.group(0),
                "snippet": snippet,
                "urls": extract_urls(snippet)
            })

            # فقط چند نمونه کافی است
            if len(matches) >= 10:
                break

        result["video_scripts"].append({
            "script_index": index,
            "type": script.get("type"),
            "matches": matches
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
                "status": "error",
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

    print()
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
