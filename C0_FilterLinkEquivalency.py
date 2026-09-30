import json
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def normalize_url(url):
    parts = urlsplit(url)

    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid"
    }

    query_params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in tracking_params
    ]

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query_params),
        ""
    ))


def filter_link_equivalency():
    with open("B1_News.json", "r", encoding="utf-8") as file:
        news_data = json.load(file)

    news = news_data.get("news", [])

    seen_urls = set()
    filtered_news = []

    for item in news:
        url = item.get("url", "")

        if not url:
            continue

        normalized_url = normalize_url(url)

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)
        filtered_news.append(item)

    with open(
        "C1_NewsAfterLinkEquivalencyRun.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {"news": filtered_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Input news: {len(news)}")
    print(f"After link equivalency: {len(filtered_news)}")
    print(f"Removed duplicates: {len(news) - len(filtered_news)}")


if __name__ == "__main__":
    filter_link_equivalency()
