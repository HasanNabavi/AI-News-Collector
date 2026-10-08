import json
import html
import requests

from bs4 import BeautifulSoup
from pathlib import Path


OUTPUT_FILE = "Test_Scrapers.json"


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


TEST_URLS = [
    {
        "title": "Changing Your Career Isn’t Easy",
        "url": "https://spectrum.ieee.org/career-pivots-for-software-engineers",
    },
    {
        "title": "The U.S. Just Bet $1 Billion on Quantum Chip Manufacturing",
        "url": "https://spectrum.ieee.org/anderon-quantum-fab",
    },
    {
        "title": "Europe’s Circuit4EU Initiative Targets Rare Earths From E-Waste",
        "url": "https://spectrum.ieee.org/e-waste-european-union-circuit4eu",
    },
]


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def normalize_text(text):
    text = html.unescape(text)
    text = text.replace("\xa0", " ")

    return " ".join(text.split())


def get_element_info(element):
    if element is None:
        return None

    return {
        "tag": element.name,
        "id": element.get("id"),
        "class": element.get("class"),
        "text": normalize_text(
            element.get_text(" ", strip=True)
        )[:1000],
    }


def get_ancestor_chain(element, max_depth=6):
    ancestors = []

    current = element

    depth = 0

    while current is not None and depth < max_depth:
        if getattr(current, "name", None):

            ancestors.append({
                "depth": depth,
                "tag": current.name,
                "id": current.get("id"),
                "class": current.get("class"),
            })

        current = current.parent
        depth += 1

    return ancestors


def inspect_articles(soup):
    results = []

    article_elements = soup.find_all("article")

    for index, article in enumerate(article_elements, start=1):

        paragraphs = article.find_all("p")
        headings = article.find_all(["h1", "h2", "h3", "h4"])
        images = article.find_all("img")
        videos = article.find_all(["video", "iframe"])

        results.append({
            "article_index": index,
            "element": get_element_info(article),
            "ancestors": get_ancestor_chain(article),

            "paragraphs": [
                {
                    "tag": p.name,
                    "class": p.get("class"),
                    "id": p.get("id"),
                    "text": normalize_text(
                        p.get_text(" ", strip=True)
                    )[:500],
                }
                for p in paragraphs
            ],

            "headings": [
                {
                    "tag": h.name,
                    "class": h.get("class"),
                    "id": h.get("id"),
                    "text": normalize_text(
                        h.get_text(" ", strip=True)
                    )[:500],
                }
                for h in headings
            ],

            "images": [
                {
                    "src": img.get("src"),
                    "srcset": img.get("srcset"),
                    "alt": img.get("alt"),
                    "class": img.get("class"),
                    "id": img.get("id"),
                }
                for img in images
            ],

            "videos": [
                {
                    "tag": video.name,
                    "src": video.get("src"),
                    "class": video.get("class"),
                    "id": video.get("id"),
                }
                for video in videos
            ],
        })

    return results


def inspect_candidate_containers(soup):
    candidates = []

    selectors = [
        "main",
        "[role='main']",
        "article",
        "[class*='article']",
        "[class*='Article']",
        "[class*='content']",
        "[class*='Content']",
        "[class*='body']",
        "[class*='Body']",
    ]

    seen = set()

    for selector in selectors:

        try:
            elements = soup.select(selector)
        except Exception:
            continue

        for element in elements:

            element_id = id(element)

            if element_id in seen:
                continue

            seen.add(element_id)

            text = normalize_text(
                element.get_text(" ", strip=True)
            )

            candidates.append({
                "selector": selector,
                "tag": element.name,
                "id": element.get("id"),
                "class": element.get("class"),
                "text_length": len(text),
                "paragraph_count": len(element.find_all("p")),
                "heading_count": len(
                    element.find_all(
                        ["h1", "h2", "h3", "h4"]
                    )
                ),
                "image_count": len(
                    element.find_all("img")
                ),
                "video_count": len(
                    element.find_all(["video", "iframe"])
                ),
                "text_preview": text[:1000],
            })

    return candidates


def inspect_links(soup):
    links = []

    for link in soup.find_all("a"):

        text = normalize_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href")

        if not text and not href:
            continue

        links.append({
            "text": text[:300],
            "href": href,
            "class": link.get("class"),
            "id": link.get("id"),
        })

    return links


def inspect_images(soup):
    images = []

    for image in soup.find_all("img"):

        images.append({
            "src": image.get("src"),
            "srcset": image.get("srcset"),
            "alt": image.get("alt"),
            "class": image.get("class"),
            "id": image.get("id"),
            "parent": get_element_info(image.parent),
        })

    return images


def inspect_videos(soup):
    videos = []

    for element in soup.find_all(["video", "iframe"]):

        videos.append({
            "tag": element.name,
            "src": element.get("src"),
            "class": element.get("class"),
            "id": element.get("id"),
            "title": element.get("title"),
            "parent": get_element_info(element.parent),
        })

    return videos


def inspect_page(item):

    result = {
        "title": item["title"],
        "url": item["url"],
        "status": "success",
    }

    try:
        html_content = get_html(item["url"])

        soup = BeautifulSoup(
            html_content,
            "html.parser"
        )

        result["html_length"] = len(html_content)

        title_tag = soup.find("title")

        result["page_title"] = (
            normalize_text(
                title_tag.get_text(" ", strip=True)
            )
            if title_tag
            else None
        )

        meta_description = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        result["meta_description"] = (
            meta_description.get("content", "")
            if meta_description
            else None
        )

        result["article_count"] = len(
            soup.find_all("article")
        )

        result["articles"] = inspect_articles(
            soup
        )

        result["candidate_containers"] = (
            inspect_candidate_containers(soup)
        )

        result["images"] = inspect_images(
            soup
        )

        result["videos"] = inspect_videos(
            soup
        )

        result["links"] = inspect_links(
            soup
        )

    except Exception as error:

        result["status"] = "error"

        result["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }

    return result


def main():

    output_path = (
        Path(__file__).resolve().parent
        / OUTPUT_FILE
    )

    results = []

    print("=" * 80)
    print("IEEE Spectrum HTML Structure Test")
    print("=" * 80)

    for index, item in enumerate(
        TEST_URLS,
        start=1
    ):

        print(
            f"\nTesting article {index}: "
            f"{item['title']}"
        )

        result = inspect_page(item)

        results.append(result)

        if result["status"] == "success":
            print(
                f"  HTML length: "
                f"{result['html_length']:,}"
            )

            print(
                f"  <article> count: "
                f"{result['article_count']}"
            )

            print(
                f"  Images: "
                f"{len(result['images'])}"
            )

            print(
                f"  Videos/iframes: "
                f"{len(result['videos'])}"
            )

        else:
            print(
                f"  ERROR: "
                f"{result['error']['message']}"
            )

    output = {
        "test": "IEEE Spectrum HTML Structure",
        "articles_tested": len(results),
        "results": results,
    }

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n" + "=" * 80)
    print("Test completed.")
    print(f"Output: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
