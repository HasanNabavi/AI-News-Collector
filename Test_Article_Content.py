import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode


RSS_URL = "https://www.technologyreview.com/feed"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def normalize_url(url):
    """
    Remove tracking parameters from a URL.
    """

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
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True
        )
        if key.lower() not in tracking_params
    ]

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query_params),
        ""
    ))


def is_download_newsletter(soup):
    """
    Detect MIT Technology Review's
    'The Download' newsletter page.
    """

    text = soup.get_text(
        " ",
        strip=True
    )

    return (
        "This is today's edition of The Download" in text
        and
        "our weekday newsletter" in text
    )


def extract_newsletter_links(soup):
    """
    Test extraction of article links from
    a MIT Technology Review newsletter page.
    """

    container = soup.select_one(
        "#content--body"
    )

    if container is None:
        return []

    results = []

    headings = container.find_all(
        ["h2", "h3", "h4"]
    )

    for heading in headings:

        heading_text = heading.get_text(
            " ",
            strip=True
        )

        if not heading_text:
            continue

        # --------------------------------------------------
        # Method 1:
        # Check if the heading itself contains a link
        # --------------------------------------------------

        links = heading.find_all(
            "a",
            href=True
        )

        # --------------------------------------------------
        # Method 2:
        # Check the parent element
        # --------------------------------------------------

        if not links:

            parent = heading.parent

            if parent is not None:
                links = parent.find_all(
                    "a",
                    href=True
                )

        # --------------------------------------------------
        # Method 3:
        # Check the next few siblings
        # --------------------------------------------------

        if not links:

            current = heading

            for _ in range(4):

                current = current.find_next_sibling()

                if current is None:
                    break

                links = current.find_all(
                    "a",
                    href=True
                )

                if links:
                    break

        # --------------------------------------------------
        # Save candidate links
        # --------------------------------------------------

        for link in links:

            href = link.get(
                "href",
                ""
            )

            if not href:
                continue

            full_url = urljoin(
                "https://www.technologyreview.com/",
                href
            )

            full_url = normalize_url(
                full_url
            )

            # Only MIT Technology Review article URLs
            if (
                "technologyreview.com/"
                in full_url
                and "/20" in full_url
            ):
                results.append({
                    "heading": heading_text,
                    "link_text": link.get_text(
                        " ",
                        strip=True
                    ),
                    "url": full_url
                })

    # Remove exact duplicate URLs
    unique_results = []
    seen_urls = set()

    for item in results:

        if item["url"] in seen_urls:
            continue

        seen_urls.add(
            item["url"]
        )

        unique_results.append(
            item
        )

    return unique_results


def test():

    print(
        "MIT Technology Review"
    )
    print(
        "Newsletter Article Link Test"
    )
    print(
        "=" * 60
    )

    feed = feedparser.parse(
        RSS_URL
    )

    print(
        f"RSS items found: "
        f"{len(feed.entries)}"
    )

    # Test first 5 RSS items
    for index, item in enumerate(
        feed.entries[:5],
        start=1
    ):

        title = item.get(
            "title",
            "No title"
        )

        url = item.get(
            "link",
            ""
        )

        print()
        print(
            "=" * 60
        )
        print(
            f"ITEM {index}"
        )
        print(
            "=" * 60
        )

        print(
            f"RSS title: {title}"
        )

        print(
            f"RSS URL: {url}"
        )

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            response.raise_for_status()

        except Exception as error:

            print(
                f"ERROR: {error}"
            )

            continue

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        if is_download_newsletter(
            soup
        ):

            print(
                "Page type: THE DOWNLOAD NEWSLETTER"
            )

            links = extract_newsletter_links(
                soup
            )

            print(
                f"Candidate article links: "
                f"{len(links)}"
            )

            for number, article in enumerate(
                links,
                start=1
            ):

                print()
                print(
                    f"[{number}]"
                )

                print(
                    f"Heading: "
                    f"{article['heading']}"
                )

                print(
                    f"Link text: "
                    f"{article['link_text']}"
                )

                print(
                    f"URL: "
                    f"{article['url']}"
                )

        else:

            print(
                "Page type: INDEPENDENT ARTICLE"
            )


if __name__ == "__main__":
    test()
