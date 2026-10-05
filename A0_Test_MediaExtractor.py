import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


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


def get_html(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.text


def make_absolute_url(
    image_url,
    article_url,
):
    if not image_url:
        return ""

    image_url = urljoin(
        article_url,
        image_url,
    )

    if image_url.startswith(
        ("http://", "https://")
    ):
        return image_url

    return ""


def extract_json_ld_image(
    soup,
    article_url,
):
    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):

        if not script.string:
            continue

        try:
            data = json.loads(
                script.string
            )
        except Exception:
            continue

        def find_image(value):

            if isinstance(value, dict):

                image = value.get(
                    "image"
                )

                if isinstance(
                    image,
                    str,
                ):
                    return image

                if isinstance(
                    image,
                    dict,
                ):
                    image_url = image.get(
                        "url"
                    )

                    if image_url:
                        return image_url

                if isinstance(
                    image,
                    list,
                ):
                    for item in image:

                        if isinstance(
                            item,
                            str,
                        ):
                            return item

                        if isinstance(
                            item,
                            dict,
                        ):
                            image_url = item.get(
                                "url"
                            )

                            if image_url:
                                return image_url

                for child in value.values():

                    if isinstance(
                        child,
                        (dict, list),
                    ):
                        result = find_image(
                            child
                        )

                        if result:
                            return result

            elif isinstance(
                value,
                list,
            ):

                for item in value:

                    result = find_image(
                        item
                    )

                    if result:
                        return result

            return None

        image = find_image(
            data
        )

        image_url = make_absolute_url(
            image,
            article_url,
        )

        if image_url:
            return image_url

    return ""


def extract_figure_image(
    soup,
    article_url,
):
    for figure in soup.find_all(
        "figure"
    ):

        img = figure.find("img")

        if not img:
            continue

        image_url = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
        )

        image_url = make_absolute_url(
            image_url,
            article_url,
        )

        if image_url:
            return image_url

    return ""


def extract_main_image(
    soup,
    article_url,
):

    # ---------------------------------------------------------
    # 1. Open Graph
    # ---------------------------------------------------------

    meta = soup.find(
        "meta",
        attrs={
            "property": "og:image"
        },
    )

    if meta:
        image_url = make_absolute_url(
            meta.get("content"),
            article_url,
        )

        if image_url:
            return image_url

    # ---------------------------------------------------------
    # 2. Twitter
    # ---------------------------------------------------------

    meta = soup.find(
        "meta",
        attrs={
            "name": "twitter:image"
        },
    )

    if meta:
        image_url = make_absolute_url(
            meta.get("content"),
            article_url,
        )

        if image_url:
            return image_url

    # ---------------------------------------------------------
    # 3. JSON-LD
    # ---------------------------------------------------------

    image_url = extract_json_ld_image(
        soup,
        article_url,
    )

    if image_url:
        return image_url

    # ---------------------------------------------------------
    # 4. Figure
    # ---------------------------------------------------------

    image_url = extract_figure_image(
        soup,
        article_url,
    )

    if image_url:
        return image_url

    return ""


def run_test():

    with open(
        "C1_NewsAfterLinkEquivalencyRun.json",
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    news = data.get(
        "news",
        []
    )

    results = []

    for item in news:

        title = item.get(
            "title",
            "",
        )

        article_url = item.get(
            "url",
            "",
        )

        image_url = ""

        try:

            html = get_html(
                article_url
            )

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            image_url = extract_main_image(
                soup,
                article_url,
            )

        except Exception:
            pass

        results.append(
            {
                "title": title,
                "article_url": article_url,
                "image_url": image_url,
            }
        )

    with open(
        "A1_Test_MediaExtractor.json",
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "Main Image Extraction Test"
    )
    print(
        "=" * 40
    )
    print(
        f"News processed: {len(results)}"
    )


if __name__ == "__main__":
    run_test()
