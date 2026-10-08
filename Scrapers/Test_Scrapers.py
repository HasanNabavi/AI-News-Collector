import json
import requests
from bs4 import BeautifulSoup

URLS = [
    "https://spectrum.ieee.org/career-pivots-for-software-engineers",
    "https://spectrum.ieee.org/anderon-quantum-fab",
    "https://spectrum.ieee.org/e-waste-european-union-circuit4eu",
]

OUTPUT_FILE = "Test_Scrapers.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


def inspect_article(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    body = soup.select_one(
        "div.body.js-expandable.clearfix.js-listicle-body"
    )

    if not body:
        return {
            "url": url,
            "status": "error",
            "error": "Main article body not found",
            "body": None,
        }

    body_description = body.select_one("div.body-description")

    if not body_description:
        return {
            "url": url,
            "status": "error",
            "error": "body-description not found",
            "body": {
                "tag": body.name,
                "class": body.get("class"),
            },
        }

    children = body_description.find_all(recursive=False)

    direct_children = []

    for index, child in enumerate(children, start=1):
        direct_children.append({
            "index": index,
            "tag": child.name,
            "class": child.get("class"),
            "id": child.get("id"),
            "text": child.get_text(" ", strip=True),
            "html": str(child),
        })

    return {
        "url": url,
        "status": "success",

        "body_selector": (
            "div.body.js-expandable.clearfix.js-listicle-body"
        ),

        "body_tag": body.name,
        "body_class": body.get("class"),

        "body_description_tag": body_description.name,
        "body_description_class": body_description.get("class"),

        "direct_children_count": len(children),

        "direct_children": direct_children,
    }


results = []

for url in URLS:
    try:
        results.append(inspect_article(url))
    except Exception as e:
        results.append({
            "url": url,
            "status": "error",
            "error": str(e),
        })


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )

print("Test completed successfully.")
print(f"Output written to: {OUTPUT_FILE}")
