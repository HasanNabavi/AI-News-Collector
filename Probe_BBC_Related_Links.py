import json
import re
import requests
from bs4 import BeautifulSoup


URLS = [
    "https://www.bbc.co.uk/news/articles/c6y9z9r4ejzwo",
    "https://www.bbc.co.uk/news/articles/c6eq84eygz0qo",
]

OUTPUT_FILE = "Probe_BBC_Related_Links_Output.json"

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
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def serialize_value(value):
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return value

    return str(value)


def get_element_info(element):
    attributes = {}

    for key, value in element.attrs.items():
        attributes[key] = serialize_value(value)

    links = []

    for link in element.find_all("a", href=True):
        link_text = clean_text(
            link.get_text(" ", strip=True)
        )

        if not link_text:
            continue

        links.append({
            "text": link_text,
            "href": link.get("href", "")
        })

    return {
        "tag": element.name,
        "attributes": attributes,
        "text": clean_text(
            element.get_text(" ", strip=True)
        ),
        "links": links
    }


def inspect_target(article, target_text):
    matches = []

    for element in article.find_all("a", href=True):
        link_text = clean_text(
            element.get_text(" ", strip=True)
        )

        if link_text != target_text:
            continue

        parents = []

        current = element

        for level in range(0, 7):
            if current is None:
                break

            info = get_element_info(current)
            info["level_from_link"] = level

            parents.append(info)

            current = current.parent

        matches.append({
            "target_text": target_text,
            "link": {
                "text": clean_text(
                    element.get_text(
                        " ",
                        strip=True
                    )
                ),
                "href": element.get(
                    "href",
                    ""
                ),
                "attributes": {
                    key: serialize_value(value)
                    for key, value in element.attrs.items()
                }
            },
            "parents": parents
        })

    return matches


def inspect_url(session, url):
    result = {
        "url": url,
        "http_status": None,
        "final_url": "",
        "html_size": 0,
        "error": "",
        "targets": []
    }

    try:
        response = session.get(
            url,
            timeout=30
        )

        result["http_status"] = response.status_code
        result["final_url"] = response.url
        result["html_size"] = len(response.content)

        response.raise_for_status()

        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        article = soup.find("article")

        if article is None:
            article = soup.find("main")

        if article is None:
            result["error"] = (
                "Article/main element not found."
            )
            return result

        for target_text in TARGET_TEXTS:
            matches = inspect_target(
                article,
                target_text
            )

            if matches:
                result["targets"].extend(
                    matches
                )

    except requests.RequestException as error:
        result["error"] = (
            f"Request error: {error}"
        )

    except Exception as error:
        result["error"] = (
            f"Unexpected error: {error}"
        )

    return result


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    output = {
        "probe": "BBC Related Links Structural Probe",
        "targets": TARGET_TEXTS,
        "urls": []
    }

    for url in URLS:
        print(f"Inspecting: {url}")

        result = inspect_url(
            session,
            url
        )

        output["urls"].append(result)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("Probe completed.")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
