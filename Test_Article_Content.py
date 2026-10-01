import requests
import feedparser
from bs4 import BeautifulSoup


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


def is_download_newsletter(soup):
    text = soup.get_text(
        " ",
        strip=True
    )

    return (
        "This is today's edition of The Download" in text
        and
        "our weekday newsletter" in text
    )


def inspect_newsletter_structure(soup):

    container = soup.select_one(
        "#content--body"
    )

    if container is None:
        print(
            "#content--body NOT FOUND"
        )
        return

    print(
        "#content--body FOUND"
    )

    print()
    print(
        "Newsletter headings and their structure:"
    )

    print(
        "=" * 70
    )

    headings = container.find_all(
        ["h2", "h3", "h4"]
    )

    for index, heading in enumerate(
        headings,
        start=1
    ):

        heading_text = heading.get_text(
            " ",
            strip=True
        )

        if not heading_text:
            continue

        print()
        print(
            f"HEADING {index}"
        )

        print(
            f"Text: {heading_text}"
        )

        print(
            f"Tag: <{heading.name}>"
        )

        # --------------------------------------------------
        # Parent information
        # --------------------------------------------------

        parent = heading.parent

        if parent is not None:

            print(
                f"Parent tag: <{parent.name}>"
            )

            parent_classes = parent.get(
                "class",
                []
            )

            if parent_classes:
                print(
                    "Parent classes: "
                    + " ".join(parent_classes)
                )

            parent_links = parent.find_all(
                "a",
                href=True
            )

            print(
                f"Links in parent: "
                f"{len(parent_links)}"
            )

            for link in parent_links:

                print(
                    "  LINK:"
                )

                print(
                    f"    Text: "
                    f"{link.get_text(' ', strip=True)}"
                )

                print(
                    f"    URL: "
                    f"{link.get('href')}"
                )

        # --------------------------------------------------
        # Grandparent information
        # --------------------------------------------------

        grandparent = None

        if parent is not None:
            grandparent = parent.parent

        if grandparent is not None:

            print(
                f"Grandparent tag: "
                f"<{grandparent.name}>"
            )

            grandparent_classes = grandparent.get(
                "class",
                []
            )

            if grandparent_classes:
                print(
                    "Grandparent classes: "
                    + " ".join(
                        grandparent_classes
                    )
                )

            grandparent_links = (
                grandparent.find_all(
                    "a",
                    href=True
                )
            )

            print(
                f"Links in grandparent: "
                f"{len(grandparent_links)}"
            )

            for link in grandparent_links:

                print(
                    "  LINK:"
                )

                print(
                    f"    Text: "
                    f"{link.get_text(' ', strip=True)}"
                )

                print(
                    f"    URL: "
                    f"{link.get('href')}"
                )

        print(
            "-" * 70
        )


def test():

    print(
        "MIT Technology Review"
    )

    print(
        "Newsletter Structure Test"
    )

    print(
        "=" * 70
    )

    feed = feedparser.parse(
        RSS_URL
    )

    print(
        f"RSS items found: "
        f"{len(feed.entries)}"
    )

    # فقط اولین Newsletter را بررسی می‌کنیم
    # چون هدف این تست شناخت ساختار HTML است.
    for index, item in enumerate(
        feed.entries[:5],
        start=1
    ):

        title = item.get(
            "title",
            ""
        )

        url = item.get(
            "link",
            ""
        )

        print()
        print(
            "=" * 70
        )

        print(
            f"ITEM {index}"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"URL: {url}"
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
                "Page type: "
                "THE DOWNLOAD NEWSLETTER"
            )

            inspect_newsletter_structure(
                soup
            )

            # فقط اولین Newsletter کافی است
            break

        else:

            print(
                "Page type: "
                "INDEPENDENT ARTICLE"
            )


if __name__ == "__main__":
    test()
