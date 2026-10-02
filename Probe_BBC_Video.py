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


def get_context(element, levels=3):
    context = []
    current = element

    for level in range(levels + 1):
        if current is None:
            break

        context.append({
            "level": level,
            "tag": current.name,
            "attrs": dict(current.attrs),
            "text": clean_text(current.get_text(" ", strip=True))[:2000],
            "html_start": str(current)[:5000]
        })

        current = current.parent

    return context


def inspect_page(url):
    print()
    print("=" * 80)
    print(f"URL: {url}")

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        },
        timeout=30
    )

    print(f"Status: {response.status_code}")
    print(f"HTML size: {len(response.text)}")

    soup = BeautifulSoup(response.text, "html.parser")

    results = {
        "url": url,
        "status_code": response.status_code,
        "html_size": len(response.text),
        "elements": {},
        "scripts_with_video_keywords": [],
        "video_like_elements": []
    }

    # ---------------------------------------------------------
    # 1. Direct media-related HTML elements
    # ---------------------------------------------------------

    selectors = [
        "video",
        "source",
        "iframe",
        "audio",
        "track",
        "[data-component*='video']",
        "[data-component*='Video']",
        "[data-testid*='video']",
        "[data-testid*='Video']",
        "[class*='video']",
        "[class*='Video']",
        "[id*='video']",
        "[id*='Video']",
    ]

    for selector in selectors:
        elements = soup.select(selector)

        if not elements:
            continue

        print()
        print(f"SELECTOR: {selector}")
        print(f"COUNT: {len(elements)}")

        selector_results = []

        for index, element in enumerate(elements):
            item = {
                "index": index,
                "tag": element.name,
                "attrs": dict(element.attrs),
                "text": clean_text(
                    element.get_text(" ", strip=True)
                )[:2000],
                "html": str(element)[:10000],
                "context": get_context(element, levels=3)
            }

            selector_results.append(item)

            print(
                f"  [{index}] "
                f"<{element.name}> "
                f"attrs={dict(element.attrs)}"
            )

        results["elements"][selector] = selector_results

    # ---------------------------------------------------------
    # 2. Search all HTML elements for video-like attributes
    # ---------------------------------------------------------

    interesting_attributes = [
        "src",
        "srcset",
        "data-src",
        "data-url",
        "data-video",
        "data-video-id",
        "data-media",
        "data-media-id",
        "data-testid",
        "data-component",
        "data-e2e",
        "data-id",
    ]

    seen = set()

    for element in soup.find_all(True):
        attrs = element.attrs

        serialized = json.dumps(
            attrs,
            ensure_ascii=False,
            sort_keys=True,
            default=str
        )

        if not re.search(
            r"(video|media|player|playlist|m3u8|mp4)",
            serialized,
            re.IGNORECASE
        ):
            continue

        key = (
            element.name,
            serialized
        )

        if key in seen:
            continue

        seen.add(key)

        item = {
            "tag": element.name,
            "attrs": dict(attrs),
            "text": clean_text(
                element.get_text(" ", strip=True)
            )[:2000],
            "html": str(element)[:10000],
            "context": get_context(element, levels=3)
        }

        results["video_like_elements"].append(item)

    print()
    print(
        f"Video-like elements found: "
        f"{len(results['video_like_elements'])}"
    )

    # ---------------------------------------------------------
    # 3. Search scripts for video-related data
    # ---------------------------------------------------------

    keywords = [
        "video",
        "media",
        "player",
        "playlist",
        "m3u8",
        "mp4",
        "manifest",
        "urn:bbc",
    ]

    for index, script in enumerate(
        soup.find_all("script")
    ):
        script_text = script.string or script.get_text()

        if not script_text:
            continue

        if not re.search(
            r"(video|media|player|playlist|m3u8|mp4|manifest|urn:bbc)",
            script_text,
            re.IGNORECASE
        ):
            continue

        matches = []

        for keyword in keywords:
            for match in re.finditer(
                keyword,
                script_text,
                re.IGNORECASE
            ):
                start = max(0, match.start() - 1000)
                end = min(
                    len(script_text),
                    match.end() + 3000
                )

                snippet = script_text[start:end]

                matches.append({
                    "keyword": keyword,
                    "snippet": snippet
                })

        item = {
            "script_index": index,
            "type": script.get("type"),
            "attrs": dict(script.attrs),
            "matches": matches[:20]
        }

        results["scripts_with_video_keywords"].append(item)

        print()
        print(
            f"SCRIPT {index}: "
            f"{len(matches)} keyword matches"
        )

    return results


def main():
    all_results = []

    for url in URLS:
        try:
            result = inspect_page(url)
            all_results.append(result)

        except Exception as error:
            all_results.append({
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
            all_results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("Probe completed.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
