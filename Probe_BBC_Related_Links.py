import re
import requests
from bs4 import BeautifulSoup


URLS = [
    "https://www.bbc.co.uk/news/articles/c6y9z9r4ejzwo",
    "https://www.bbc.co.uk/news/articles/c6eq84eygz0qo",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


TARGET_TEXTS = [
    "Three takeaways from Trump's 'Super Intelligence' summit",
    "OpenAI says its rogue AI tried to hack other companies",
    "OpenAI scraps rollout of new model over safety concerns",
    "Brutal crypto attack on couple prompts £10k reward",
    "How crypto criminals stole $700 million from people - often using age-old tricks",
]


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def print_element_info(element, level):
    print()
    print(f"--- Parent level {level} ---")

    print("TAG:")
    print(element.name)

    print("ID:")
    print(element.get("id", ""))

    print("CLASS:")
    print(element.get("class", []))

    print("ARIA:")
    for key, value in element.attrs.items():
        if key.startswith("aria-"):
            print(f"  {key} = {value}")

    print("DATA ATTRIBUTES:")
    for key, value in element.attrs.items():
        if key.startswith("data-"):
            print(f"  {key} = {value}")

    print("HREFS:")
    links = element.find_all("a", href=True)

    for link in links:
        text = clean_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href", "")

        if text:
            print(f"  TEXT: {text}")
            print(f"  HREF: {href}")

    element_text = clean_text(
        element.get_text(" ", strip=True)
    )

    print("TEXT:")
    print(element_text[:1000])


def inspect_target(soup, target_text):
    matches = []

    for element in soup.find_all("a", href=True):
        link_text = clean_text(
            element.get_text(" ", strip=True)
        )

        if link_text == target_text:
            matches.append(element)

    if not matches:
        return False

    for match_number, link in enumerate(matches, start=1):
        print()
        print("=" * 80)
        print(f"TARGET MATCH {match_number}")
        print("=" * 80)
        print(f"TARGET TEXT:\n{target_text}")
        print()
        print("LINK TAG:")
        print(link)

        current = link

        for level in range(1, 6):
            current = current.parent

            if current is None:
                break

            print_element_info(
                current,
                level
            )

    return True


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    for url in URLS:
        print()
        print("#" * 100)
        print("URL")
        print(url)
        print("#" * 100)

        try:
            response = session.get(
                url,
                timeout=30
            )

            print(f"HTTP STATUS: {response.status_code}")
            print(f"FINAL URL: {response.url}")
            print(f"HTML SIZE: {len(response.content)}")

            response.raise_for_status()

            soup = BeautifulSoup(
                response.content,
                "html.parser"
            )

            article = soup.find("article")

            if article is None:
                article = soup.find("main")

            if article is None:
                print("ARTICLE/MAIN NOT FOUND")
                continue

            found_count = 0

            for target_text in TARGET_TEXTS:
                found = inspect_target(
                    article,
                    target_text
                )

                if found:
                    found_count += 1

            print()
            print("=" * 100)
            print("SUMMARY")
            print("=" * 100)
            print(f"Related targets found: {found_count}")

        except requests.RequestException as error:
            print(f"REQUEST ERROR: {error}")

        except Exception as error:
            print(f"UNEXPECTED ERROR: {error}")


if __name__ == "__main__":
    main()
