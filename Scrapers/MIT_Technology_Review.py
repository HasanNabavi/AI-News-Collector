import requests
from bs4 import BeautifulSoup


def scrape(url):
    """
    Scrape an article from MIT Technology Review.

    Returns a standardized article structure.
    """

    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    return {
        "title": "",
        "text": "",
        "author": "",
        "published_at": "",
        "main_image": "",
        "images": [],
        "videos": [],
        "url": url
    }
