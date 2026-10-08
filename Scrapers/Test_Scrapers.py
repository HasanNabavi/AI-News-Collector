import json
import requests
from bs4 import BeautifulSoup


URL = "https://spectrum.ieee.org/career-pivots-for-software-engineers"

OUTPUT_FILE = "Test_Scrapers.json"


headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")


body = soup.select_one(
    "div.body.js-expandable.clearfix.js-listicle-body"
)


if not body:
    result = {
        "url": URL,
        "status": "error",
        "error": "Main article body not found",
        "direct_children": []
    }

else:

    children = body.find_all(recursive=False)

    direct_children = []

    for index, child in enumerate(children, start=1):

        text = child.get_text(" ", strip=True)

        direct_children.append({
            "index": index,
            "tag": child.name,
            "class": child.get("class"),
            "id": child.get("id"),
            "text": text,
            "html": str(child)
        })


    result = {
        "url": URL,
        "status": "success",
        "body_selector": "div.body.js-expandable.clearfix.js-listicle-body",
        "body_tag": body.name,
        "body_class": body.get("class"),
        "direct_children_count": len(children),
        "direct_children": direct_children
    }


# ---------------------------------------------------------
# Create / overwrite Test_Scrapers.json
# ---------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)


print(f"Test completed successfully.")
print(f"Output written to: {OUTPUT_FILE}")
