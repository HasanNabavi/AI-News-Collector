import requests
from bs4 import BeautifulSoup


URL = "https://spectrum.ieee.org/career-pivots-for-software-engineers"


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
    print("BODY NOT FOUND")
    raise SystemExit(1)


print("=" * 100)
print("BODY FOUND")
print("=" * 100)

print(f"Tag   : {body.name}")
print(f"Class : {body.get('class')}")
print()


children = body.find_all(recursive=False)

print(f"Direct children: {len(children)}")
print()


for index, child in enumerate(children, start=1):

    text = child.get_text(" ", strip=True)

    if len(text) > 250:
        text = text[:250] + "..."

    print("-" * 100)
    print(f"CHILD #{index}")
    print(f"Tag     : {child.name}")
    print(f"Class   : {child.get('class')}")
    print(f"ID      : {child.get('id')}")
    print(f"Text    : {text}")
    print()

print("=" * 100)
print("RAW HTML OF DIRECT CHILDREN")
print("=" * 100)

for index, child in enumerate(children, start=1):

    print()
    print(f"### CHILD #{index}")
    print(child.prettify())
