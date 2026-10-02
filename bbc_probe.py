import json
import sys
from collections import Counter

import requests
from bs4 import BeautifulSoup


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def probe(session, url, number):
    response = session.get(url, timeout=20)

    filename = f"bbc_sample_{number}.html"

    with open(filename, "w", encoding="utf-8") as file:
        file.write(response.text)

    print("=" * 70)
    print(f"URL: {url}")
    print(f"Status code: {response.status_code}")
    print(f"Final URL: {response.url}")
    print(f"HTML size: {len(response.text)} bytes")
    print(f"Saved HTML: {filename}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Title
    print("\n[TITLE]")
    print(
        soup.title.get_text(strip=True)
        if soup.title
        else "None"
    )

    # H1
    print("\n[H1]")
    print([
        h.get_text(" ", strip=True)[:200]
        for h in soup.find_all("h1")
    ])

    # Metadata
    print("\n[META]")

    for meta in soup.find_all("meta"):
        key = meta.get("property") or meta.get("name") or ""

        if (
            key.startswith(("og:", "article:", "twitter:"))
            or key in (
                "description",
                "author",
                "pubdate",
                "lastmod"
            )
        ):
            value = meta.get("content") or ""
            print(f"{key} = {value[:300]}")

    # JSON-LD
    print("\n[JSON-LD]")

    jsonld_blocks = soup.find_all(
        "script",
        type="application/ld+json"
    )

    print(f"Number of JSON-LD blocks: {len(jsonld_blocks)}")

    for index, block in enumerate(jsonld_blocks):
        try:
            data = json.loads(
                block.string or block.get_text() or ""
            )

            print(f"\nJSON-LD block {index}:")
            print(
                json.dumps(
                    data,
                    ensure_ascii=False
                )[:2000]
            )

        except Exception as error:
            print(
                f"JSON-LD block {index} could not be parsed: "
                f"{error}"
            )

    # BBC data-component structure
    print("\n[DATA-COMPONENT]")

    components = soup.find_all(
        attrs={"data-component": True}
    )

    counts = Counter(
        tag["data-component"]
        for tag in components
    )

    print("Component counts:")
    print(dict(counts))

    seen = set()

    print("\nFirst example of each component:")

    for tag in components:
        name = tag["data-component"]

        if name in seen:
            continue

        seen.add(name)

        text = tag.get_text(
            " ",
            strip=True
        )[:300]

        print(
            f"- {name} | "
            f"tag={tag.name} | "
            f"text={text}"
        )

    # Article / main
    print("\n[STRUCTURE]")

    print(
        "article tags:",
        len(soup.find_all("article"))
    )

    print(
        "main tags:",
        len(soup.find_all("main"))
    )

    # Time
    print("\n[TIME]")

    print([
        (
            tag.get("datetime"),
            tag.get_text(strip=True)
        )
        for tag in soup.find_all("time")
    ])

    # Images
    print("\n[IMAGES]")

    images = soup.find_all("img")

    print(
        f"Number of images: {len(images)}"
    )

    print(
        "Images with srcset:",
        sum(
            bool(image.get("srcset"))
            for image in images
        )
    )

    for image in images[:10]:

        attributes = {
            key: str(image.get(key))[:200]
            for key in (
                "src",
                "srcset",
                "data-src",
                "alt",
                "loading"
            )
            if image.get(key)
        }

        print(attributes)

    # Videos
    print("\n[VIDEOS]")

    videos = soup.find_all("video")
    iframes = soup.find_all("iframe")

    print(
        "video tags:",
        len(videos)
    )

    print(
        "iframe tags:",
        len(iframes)
    )

    for tag in (videos + iframes)[:10]:

        attributes = {
            key: str(tag.get(key))[:200]
            for key in (
                "src",
                "poster",
                "data-src"
            )
            if tag.get(key)
        }

        print(
            f"{tag.name}: {attributes}"
        )


def main():

    urls = [
        "https://www.bbc.co.uk/news/articles/c6y9z9r4ejzwo",
        "https://www.bbc.co.uk/news/articles/c6eq84eygz0qo"
    ]

    session = requests.Session()

    session.headers.update({
        "User-Agent": UA,
        "Accept-Language": "en-GB,en;q=0.9"
    })

    for number, url in enumerate(urls, start=1):

        try:
            probe(
                session,
                url,
                number
            )

        except Exception as error:

            print("=" * 70)
            print(f"FAILED: {url}")
            print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
