import html
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


__all__ = ["scrape"]


ALLOWED_HOSTS = {
    "technologyreview.com",
    "www.technologyreview.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = (10, 30)

MAX_ATTEMPTS = 3
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_ERROR_BODY_BYTES = 200 * 1024

MAX_RETRY_AFTER_SECONDS = 30.0
BACKOFF_BASE_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 8.0

MIN_BODY_CHARS = 300
DEDUP_MIN_CHARS = 40

MAX_SINGLE_PRUNE_FRACTION = 0.35
MAX_TOTAL_PRUNE_FRACTION = 0.50
MAX_TAIL_REMOVALS = 5
MAX_TAIL_BLOCK_CHARS = 500

MAX_AUTHOR_LENGTH = 120
MAX_AUTHORS = 6

MAX_REASONABLE_IMAGE_WIDTH = 2400

MAX_JSON_LD_NODES = 2000
MAX_JSON_LD_DEPTH = 10


REDIRECT_STATUSES = {301, 302, 303, 307, 308}

RETRYABLE_STATUSES = {
    429,
    500,
    502,
    503,
    504,
}

LOGIN_PATH_PREFIXES = (
    "/login",
    "/signin",
    "/sign-in",
    "/subscribe",
    "/account",
    "/consent",
)

BLOCK_TITLE_PREFIXES = (
    "just a moment",
    "attention required",
    "access denied",
    "are you a robot",
    "verify you are human",
    "please verify",
    "you have been blocked",
    "page not found",
    "404 not found",
    "404 error",
    "error 404",
    "403 forbidden",
    "error 1020",
)

CHALLENGE_MARKERS = (
    "enable javascript and cookies to continue",
    "checking your browser before accessing",
    "cf-browser-verification",
    "cf_chl_opt",
    "cf-chl-bypass",
    "needs to review the security of your connection",
    "verify you are human by completing",
)

ARTICLE_TYPES = {
    "article",
    "newsarticle",
    "reportage",
    "blogposting",
    "techarticle",
    "analysisnewsarticle",
    "opinionnewsarticle",
    "reviewnewsarticle",
    "report",
}

ARTICLE_PATH_RE = re.compile(
    r"^/\d{4}/\d{2}/\d{2}/\d+/"
)

NEWSLETTER_TITLE_RE = re.compile(
    r"^the download\s*(?::|-|\u2013|\u2014|$)",
    re.I,
)

SKIPPED_PAGE_TYPES = {
    "newsletter",
    "podcast",
    "video",
}


HARD_REMOVE_TAGS = [
    "script",
    "style",
    "noscript",
    "template",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    "svg",
    "nav",
    "footer",
]

CARD_NOISE_TOKENS = {
    "related",
    "related-stories",
    "related-articles",
    "related-posts",
    "related-content",
    "related-reading",
    "recommended",
    "recommendations",
    "recommended-stories",
    "more-stories",
    "most-popular",
    "trending",
    "read-next",
    "keep-reading",
    "comments",
    "comment-section",
    "newsletter",
    "newsletter-signup",
    "newsletter-form",
    "newsletter-promo",
}

NOISE_CLASS_TOKENS = CARD_NOISE_TOKENS | {
    "subscribe",
    "subscription",
    "subscription-promo",
    "social",
    "social-share",
    "social-links",
    "share",
    "share-buttons",
    "share-bar",
    "sharing",
    "advert",
    "advertisement",
    "ad",
    "ads",
    "ad-slot",
    "ad-container",
    "promo",
    "promo-box",
    "promotion",
    "author-bio",
    "author-box",
    "author-info",
    "byline",
}

P_NOISE_CLASS_TOKENS = {
    "byline",
    "caption",
    "credit",
    "photo-credit",
    "image-credit",
    "advertisement",
    "promo",
    "newsletter-signup",
}

NOISE_CONTAINER_TAGS = [
    "div",
    "section",
    "aside",
    "ul",
    "ol",
    "header",
    "footer",
    "nav",
]

NOISE_ROLES = {
    "complementary",
    "navigation",
    "banner",
    "contentinfo",
}

NOISE_IDS = {
    "comments",
    "respond",
    "newsletter",
    "newsletter-signup",
    "related",
    "related-posts",
    "recommended",
    "share",
    "social",
    "social-share",
    "sidebar",
}

BLOCK_TAGS = [
    "p",
    "li",
    "blockquote",
    "h2",
    "h3",
    "h4",
]

INNER_BLOCK_NAMES = {
    "ul",
    "ol",
    "li",
    "p",
    "blockquote",
    "h2",
    "h3",
    "h4",
    "figure",
    "table",
    "script",
    "style",
}

BYLINE_SKIP_NAMES = {
    "time",
    "script",
    "style",
}

SKIP_BLOCK_RE = re.compile(
    r"^(?:advertisement|sponsored content|"
    r"story continues below|back to top)$",
    re.I,
)

TAIL_BOILERPLATE_PATTERNS = (
    re.compile(
        r"^this (?:article|story|piece|essay) "
        r"(?:first |originally )?"
        r"(?:appeared|was published|ran) in\b",
        re.I,
    ),
    re.compile(
        r"^(?:to )?(?:receive|get) "
        r"(?:it|this|the|our|these)\b.{0,120}"
        r"\b(?:inbox|newsletter)\b",
        re.I,
    ),
    re.compile(
        r"^(?:sign up|subscribe|subscribers)\b"
        r".{0,200}\b(?:newsletter|inbox|here)\b",
        re.I,
    ),
    re.compile(
        r"^want (?:more|to read more)\b"
        r".{0,200}\b(?:newsletter|subscribe|inbox)\b",
        re.I,
    ),
    re.compile(
        r"^(?:read|see) (?:more|next|also)\b",
        re.I,
    ),
    re.compile(
        r"^(?:keep reading|related stories|related reading|"
        r"most popular|recommended reading)\b",
        re.I,
    ),
)

STANDFIRST_CLASS_RE = re.compile(
    r"(?:(?<![a-z])"
    r"(?:standfirst|dek|subtitle|subhead(?:line)?)"
    r"(?![a-z]))"
    r"|(?:(?:Standfirst|Dek|Subtitle|Subhead(?:line)?)"
    r"(?![a-z]))"
)

BYLINE_SELECTOR = (
    '[itemprop="author"], [class*="byline"], [class*="Byline"], '
    '[class*="author-name"], [class*="authorName"]'
)

GENERIC_AUTHOR_NAMES = {
    "mit technology review",
    "technology review",
    "admin",
    "administrator",
}

URL_LIKE_RE = re.compile(
    r"^(?:https?:)?//|^www\.",
    re.I,
)

ENTITY_RE = re.compile(
    r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|"
    r"[A-Za-z][A-Za-z0-9]{1,31});"
)

ZERO_WIDTH_RE = re.compile(
    "[\u200b\u2060\ufeff\u00ad]"
)

SPACE_TRANSLATION = {
    ord("\xa0"): " ",
    ord("\u202f"): " ",
    ord("\u2007"): " ",
}

TITLE_SUFFIX_RE = re.compile(
    r"\s*[|\u2013\u2014-]\s*MIT Technology Review\s*$",
    re.I,
)

IMAGE_EXTENSION_RE = re.compile(
    r"\.(?:jpe?g|png|gif|webp|avif|svg)$",
    re.I,
)

TRACKING_IMAGE_RE = re.compile(
    r"(?:/|[_.-])"
    r"(?:pixel|spacer|1x1|tracking|beacon)"
    r"(?:[/_.-]|$)",
    re.I,
)

VIDEO_HOST_SUFFIXES = (
    "youtube.com",
    "youtube-nocookie.com",
    "youtu.be",
    "vimeo.com",
)


SESSION = requests.Session()
SESSION.headers.update(HEADERS)


class ScrapeError(Exception):
    pass


def _empty_result(url):
    return {
        "page_type": "",
        "title": "",
        "text": "",
        "author": "",
        "published_at": "",
        "standfirst": "",
        "main_image": "",
        "images": [],
        "videos": [],
        "url": url,
    }


def _error_result(url, message):
    result = _empty_result(url)
    result["status"] = "error"
    result["error"] = message
    return result


def _unescape_entities(value):
    for _ in range(3):
        if not ENTITY_RE.search(value):
            break

        unescaped = html.unescape(value)

        if unescaped == value:
            break

        value = unescaped

    return value


def normalize_text(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = _unescape_entities(value)
    value = unicodedata.normalize("NFC", value)
    value = value.translate(SPACE_TRANSLATION)
    value = ZERO_WIDTH_RE.sub("", value)

    return " ".join(value.split())


def normalize_url(value, base_url):
    if not isinstance(value, str):
        return ""

    value = _unescape_entities(value.strip())

    if not value:
        return ""

    if value.lower().startswith(
        ("data:", "javascript:", "blob:", "about:")
    ):
        return ""

    if value.startswith("//"):
        value = "https:" + value

    try:
        absolute = urljoin(base_url, value)
        parsed = urlparse(absolute)
    except ValueError:
        return ""

    if parsed.scheme not in ("http", "https"):
        return ""

    if not parsed.netloc:
        return ""

    return parsed._replace(fragment="").geturl()


def own_text(element, skip_names=INNER_BLOCK_NAMES):
    parts = []

    for child in element.children:
        if isinstance(child, Tag):
            if child.name in skip_names:
                continue

            if child.name == "br":
                parts.append(" ")
                continue

            if child.name in ("script", "style"):
                continue

            parts.append(own_text(child, skip_names))

        elif isinstance(child, NavigableString):
            parts.append(str(child))

    return "".join(parts)


def _validate_url(value):
    if not isinstance(value, str) or not value.strip():
        raise ScrapeError("invalid URL")

    try:
        parsed = urlparse(value.strip())
        port = parsed.port
    except ValueError:
        raise ScrapeError("invalid URL")

    if parsed.scheme != "https":
        raise ScrapeError("URL must use HTTPS")

    host = (parsed.hostname or "").lower()

    if host not in ALLOWED_HOSTS:
        raise ScrapeError(
            "URL host is not an allowed MIT Technology Review domain: "
            + (host or value)
        )

    if parsed.username or parsed.password:
        raise ScrapeError(
            "URL must not contain credentials"
        )

    if port not in (None, 443):
        raise ScrapeError(
            "URL uses an unsupported port"
        )

    return parsed._replace(
        netloc=host,
        fragment="",
    ).geturl()


def _validate_redirect(value):
    try:
        return _validate_url(value)
    except ScrapeError as error:
        raise ScrapeError(
            "redirect rejected: " + str(error)
        )


def _parse_retry_after(header):
    header = header.strip()

    try:
        return float(header)
    except ValueError:
        pass

    try:
        moment = parsedate_to_datetime(header)

        if moment.tzinfo is None:
            moment = moment.replace(
                tzinfo=timezone.utc
            )

        return (
            moment - datetime.now(timezone.utc)
        ).total_seconds()

    except (
        TypeError,
        ValueError,
        IndexError,
    ):
        return None


def _retry_delay(response, attempt):
    header = response.headers.get("Retry-After")

    if header:
        seconds = _parse_retry_after(header)

        if seconds is not None:
            if seconds > MAX_RETRY_AFTER_SECONDS:
                return None

            return max(seconds, 0.0)

    return min(
        BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
        MAX_BACKOFF_SECONDS,
    )


def _has_challenge_header(response):
    return (
        response.headers.get(
            "cf-mitigated",
            "",
        ).strip().lower()
        == "challenge"
    )


def _get_with_retries(url):
    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):
        try:
            response = SESSION.get(
                url,
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )

        except (
            requests.ConnectionError,
            requests.Timeout,
        ) as error:

            if attempt < MAX_ATTEMPTS:
                time.sleep(
                    min(
                        BACKOFF_BASE_SECONDS
                        * (2 ** (attempt - 1)),
                        MAX_BACKOFF_SECONDS,
                    )
                )
                continue

            raise ScrapeError(
                "request failed after retries: "
                + str(error)
            )

        except requests.RequestException as error:
            raise ScrapeError(
                "request failed: " + str(error)
            )

        if (
            response.status_code
            in RETRYABLE_STATUSES
            and attempt < MAX_ATTEMPTS
            and not _has_challenge_header(response)
        ):
            delay = _retry_delay(
                response,
                attempt,
            )

            if delay is None:
                return response

            response.close()
            time.sleep(delay)
            continue

        return response

    raise ScrapeError("request failed")


def _read_body(
    response,
    limit,
    truncate=False,
):
    length = response.headers.get(
        "Content-Length",
        "",
    )

    if (
        not truncate
        and length.isdigit()
        and int(length) > limit
    ):
        raise ScrapeError(
            "response too large"
        )

    chunks = []
    size = 0

    try:
        for chunk in response.iter_content(
            chunk_size=65536
        ):
            if not chunk:
                continue

            size += len(chunk)

            if size > limit:
                if truncate:
                    remaining = (
                        limit
                        - (
                            size
                            - len(chunk)
                        )
                    )

                    chunks.append(
                        chunk[:remaining]
                    )
                    break

                raise ScrapeError(
                    "response too large"
                )

            chunks.append(chunk)

    except requests.RequestException as error:
        raise ScrapeError(
            "failed to read response body: "
            + str(error)
        )

    return b"".join(chunks)


def _looks_like_challenge(content):
    head = content[:100000].decode(
        "utf-8",
        "ignore",
    ).lower()

    return any(
        marker in head
        for marker in CHALLENGE_MARKERS
    )


def _http_error_message(status, response):
    if status == 429:
        retry_after = response.headers.get(
            "Retry-After"
        )

        suffix = (
            ", Retry-After: "
            + retry_after
            if retry_after
            else ""
        )

        return (
            "rate limited (HTTP 429"
            + suffix
            + ")"
        )

    if status in (404, 410):
        return (
            "article not found (HTTP "
            + str(status)
            + ")"
        )

    if status in (401, 402, 403):
        return (
            "access denied (HTTP "
            + str(status)
            + ")"
        )

    if status >= 500:
        return (
            "server error (HTTP "
            + str(status)
            + ")"
        )

    return (
        "unexpected HTTP status "
        + str(status)
    )


def _read_final_response(response):
    status = response.status_code

    if status >= 300:
        try:
            body = _read_body(
                response,
                MAX_ERROR_BODY_BYTES,
                truncate=True,
            )
        except ScrapeError:
            body = b""

        if (
            _has_challenge_header(response)
            or _looks_like_challenge(body)
        ):
            raise ScrapeError(
                "blocked by an anti-bot challenge "
                "(HTTP "
                + str(status)
                + ")"
            )

        raise ScrapeError(
            _http_error_message(
                status,
                response,
            )
        )

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if (
        content_type
        and "html" not in content_type
        and "xml" not in content_type
    ):
        raise ScrapeError(
            "unexpected content type: "
            + content_type
        )

    body = _read_body(
        response,
        MAX_RESPONSE_BYTES,
    )

    if not body.strip():
        raise ScrapeError(
            "empty response body"
        )

    return body


def _fetch(url):
    current = url

    for _ in range(MAX_REDIRECTS + 1):
        response = _get_with_retries(current)

        try:
            location = response.headers.get(
                "Location"
            )

            if (
                response.status_code
                in REDIRECT_STATUSES
                and location
            ):
                current = _validate_redirect(
                    urljoin(
                        current,
                        location,
                    )
                )
                continue

            return (
                _read_final_response(response),
                current,
            )

        finally:
            response.close()

    raise ScrapeError(
        "too many redirects"
    )


def _check_not_blocked(
    soup,
    content,
    requested_url,
    final_url,
):
    final_path = urlparse(
        final_url
    ).path.lower()

    requested_path = urlparse(
        requested_url
    ).path.lower()

    if (
        final_path.startswith(
            LOGIN_PATH_PREFIXES
        )
        and not requested_path.startswith(
            LOGIN_PATH_PREFIXES
        )
    ):
        raise ScrapeError(
            "redirected to a login, subscription "
            "or consent page"
        )

    if (
        final_path in ("", "/")
        and requested_path not in ("", "/")
    ):
        raise ScrapeError(
            "redirected to the home page "
            "(article unavailable)"
        )

    title = ""

    if soup.title:
        title = normalize_text(
            soup.title.get_text()
        )

    if title.casefold().startswith(
        BLOCK_TITLE_PREFIXES
    ):
        raise ScrapeError(
            "blocked or unavailable page: "
            + title
        )

    if _looks_like_challenge(content):
        raise ScrapeError(
            "anti-bot challenge page returned "
            "instead of the article"
        )


def collect_meta(soup):
    meta = {}

    for tag in soup.find_all("meta"):
        content = tag.get("content")

        if (
            not isinstance(content, str)
            or not content.strip()
        ):
            continue

        for attribute in (
            "property",
            "name",
            "itemprop",
        ):
            key = tag.get(attribute)

            if (
                isinstance(key, str)
                and key.strip()
            ):
                meta.setdefault(
                    key.strip().lower(),
                    [],
                ).append(
                    content.strip()
                )

    return meta


def meta_first(meta, *keys):
    for key in keys:
        values = meta.get(key)

        if values:
            return values[0]

    return ""


def node_types(node):
    raw = node.get("@type")

    if isinstance(raw, str):
        raw = [raw]

    if not isinstance(raw, list):
        return set()

    types = set()

    for item in raw:
        if isinstance(item, str):
            types.add(
                item.strip()
                .rsplit("/", 1)[-1]
                .rsplit(":", 1)[-1]
                .lower()
            )

    return types


def iter_json_ld_nodes(data):
    nodes = []
    stack = [(data, 0)]

    while (
        stack
        and len(nodes) < MAX_JSON_LD_NODES
    ):
        item, depth = stack.pop()

        if depth > MAX_JSON_LD_DEPTH:
            continue

        if isinstance(item, list):
            for child in reversed(item):
                stack.append(
                    (child, depth + 1)
                )

        elif isinstance(item, dict):
            nodes.append(item)

            for value in reversed(
                list(item.values())
            ):
                if isinstance(
                    value,
                    (dict, list),
                ):
                    stack.append(
                        (value, depth + 1)
                    )

    return nodes


def load_json_ld(soup):
    nodes = []

    for script in soup.find_all(
        "script",
        attrs={
            "type": re.compile(
                r"ld\+json",
                re.I,
            )
        },
    ):
        raw = (
            script.string
            or script.get_text()
        )

        if (
            not raw
            or not raw.strip()
        ):
            continue

        try:
            data = json.loads(
                raw,
                strict=False,
            )

        except (
            ValueError,
            TypeError,
            RecursionError,
        ):
            continue

        nodes.extend(
            iter_json_ld_nodes(data)
        )

    return nodes


def article_nodes(nodes):
    return [
        node
        for node in nodes
        if node_types(node)
        & ARTICLE_TYPES
    ]


def json_ld_get(nodes, key):
    for node in article_nodes(nodes):
        value = node.get(key)

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


def json_ld_string(nodes, key):
    value = json_ld_get(
        nodes,
        key,
    )

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        for item in value:
            if (
                isinstance(item, str)
                and item.strip()
            ):
                return item

    return ""


def _same_page(value, page_url):
    if isinstance(value, dict):
        value = (
            value.get("@id")
            or value.get("url")
        )

    if not isinstance(value, str):
        return False

    path = urlparse(value).path.rstrip("/")

    return bool(path) and (
        path
        == urlparse(page_url)
        .path.rstrip("/")
    )


def primary_article_node(
    nodes,
    page_url,
):
    candidates = article_nodes(nodes)

    for node in candidates:
        if (
            _same_page(
                node.get(
                    "mainEntityOfPage"
                ),
                page_url,
            )
            or _same_page(
                node.get("url"),
                page_url,
            )
        ):
            return node

    if len(candidates) == 1:
        return candidates[0]

    return None


def _urls_from_value(
    value,
    depth=0,
):
    if depth > 3 or value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        urls = []

        for item in value:
            urls.extend(
                _urls_from_value(
                    item,
                    depth + 1,
                )
            )

        return urls

    if isinstance(value, dict):
        for key in (
            "url",
            "contentUrl",
            "embedUrl",
        ):
            inner = value.get(key)

            if (
                isinstance(inner, str)
                and inner.strip()
            ):
                return [inner]

    return []


def _all_node_types(nodes):
    types = set()

    for node in nodes:
        types |= node_types(node)

    return types


def _strip_site_suffix(title):
    return TITLE_SUFFIX_RE.sub(
        "",
        title,
    ).strip()


def _first_h1_text(soup):
    heading = soup.find("h1")

    if heading is None:
        return ""

    return normalize_text(
        heading.get_text()
    )


def extract_title(
    soup,
    meta,
    nodes,
):
    candidates = [
        meta_first(
            meta,
            "og:title",
        ),
        json_ld_string(
            nodes,
            "headline",
        ),
        _first_h1_text(soup),
    ]

    for value in candidates:
        title = _strip_site_suffix(
            normalize_text(value)
        )

        if title:
            return title

    if soup.title:
        return _strip_site_suffix(
            normalize_text(
                soup.title.get_text()
            )
        )

    return ""


def _inside_related(element):
    for parent in element.parents:
        if (
            isinstance(parent, Tag)
            and (
                _class_segments(parent)
                & CARD_NOISE_TOKENS
            )
        ):
            return True

    return False


def extract_standfirst(
    soup,
    meta,
    nodes,
    title,
):
    candidates = [
        meta_first(
            meta,
            "description",
        ),
        meta_first(
            meta,
            "og:description",
        ),
        meta_first(
            meta,
            "twitter:description",
        ),
        json_ld_string(
            nodes,
            "description",
        ),
    ]

    for value in candidates:
        text = normalize_text(value)

        if (
            text
            and text.casefold()
            != title.casefold()
        ):
            return text

    for element in soup.find_all(
        class_=STANDFIRST_CLASS_RE
    ):
        if _inside_related(element):
            continue

        text = normalize_text(
            element.get_text()
        )

        if (
            10 <= len(text) <= 600
            and text.casefold()
            != title.casefold()
        ):
            return text

    return ""


def extract_published_at(
    soup,
    meta,
    nodes,
):
    for key in (
        "article:published_time",
        "og:article:published_time",
        "datepublished",
        "parsely-pub-date",
    ):
        value = normalize_text(
            meta_first(meta, key)
        )

        if value:
            return value

    for key in (
        "datePublished",
        "dateCreated",
    ):
        value = normalize_text(
            json_ld_string(
                nodes,
                key,
            )
        )

        if value:
            return value

    scope = (
        soup.find("article")
        or soup
    )

    for time_tag in scope.find_all(
        "time",
        attrs={"datetime": True},
    ):
        if _inside_related(time_tag):
            continue

        value = normalize_text(
            time_tag.get(
                "datetime",
                "",
            )
        )

        if (
            value
            and re.search(
                r"\d",
                value,
            )
        ):
            return value

    return ""


def clean_author_name(raw):
    name = normalize_text(raw)

    name = re.sub(
        r"^by\s+",
        "",
        name,
        flags=re.I,
    ).strip(
        " ,;-|\u2022\u00b7"
    )

    if not name:
        return ""

    if len(name) > MAX_AUTHOR_LENGTH:
        return ""

    if URL_LIKE_RE.match(name):
        return ""

    if name.startswith("@"):
        return ""

    if name.casefold() in GENERIC_AUTHOR_NAMES:
        return ""

    return name


def _unique(values):
    seen = set()
    unique_values = []

    for value in values:
        key = value.casefold()

        if key not in seen:
            seen.add(key)
            unique_values.append(value)

    return unique_values


def _join_authors(names):
    names = _unique(
        [
            name
            for name in names
            if name
        ]
    )

    return ", ".join(
        names[:MAX_AUTHORS]
    )


def _author_names_from_value(
    value,
    id_map,
    depth=0,
):
    if depth > 4 or value is None:
        return []

    if isinstance(value, str):
        name = clean_author_name(value)

        return [name] if name else []

    if isinstance(value, list):
        names = []

        for item in value:
            names.extend(
                _author_names_from_value(
                    item,
                    id_map,
                    depth + 1,
                )
            )

        return names

    if isinstance(value, dict):
        name = value.get("name")

        if (
            isinstance(name, str)
            and name.strip()
        ):
            cleaned = clean_author_name(
                name
            )

            return (
                [cleaned]
                if cleaned
                else []
            )

        reference = value.get("@id")

        if isinstance(
            reference,
            str,
        ):
            target = id_map.get(
                reference
            )

            if (
                target is not None
                and target is not value
            ):
                return (
                    _author_names_from_value(
                        target,
                        id_map,
                        depth + 1,
                    )
                )

    return []


def _author_from_json_ld(nodes):
    id_map = {}

    for node in nodes:
        identifier = node.get("@id")

        if isinstance(
            identifier,
            str,
        ):
            id_map.setdefault(
                identifier,
                node,
            )

    for node in article_nodes(nodes):
        for key in (
            "author",
            "creator",
        ):
            names = _author_names_from_value(
                node.get(key),
                id_map,
            )

            if names:
                return _join_authors(
                    names
                )

    return ""


def _names_from_link_group(links):
    if not links:
        return []

    first = links[0]
    container = first.parent

    if (
        container is not None
        and len(
            container.find_all("a")
        ) == 1
        and container.parent is not None
    ):
        container = container.parent

    group = (
        container.find_all("a")
        if container is not None
        else [first]
    )

    known = {
        id(link)
        for link in links
    }

    names = []

    for link in group:
        if id(link) in known:
            name = clean_author_name(
                link.get_text()
            )

            if name:
                names.append(name)

    return names


def _author_from_links(soup):
    for selector in (
        'a[rel~="author"]',
        'a[href*="/author/"]',
    ):
        links = [
            link
            for link in soup.select(
                selector
            )
            if not _inside_related(link)
        ]

        names = _names_from_link_group(
            links
        )

        if names:
            return _join_authors(
                names
            )

    return ""


def _author_from_byline(soup):
    for element in soup.select(
        BYLINE_SELECTOR
    ):
        if (
            element.name == "meta"
            or _inside_related(element)
        ):
            continue

        name_element = element.find(
            attrs={"itemprop": "name"}
        )

        raw = own_text(
            name_element or element,
            BYLINE_SKIP_NAMES,
        )

        first_part = re.split(
            r"[|\u2022\u00b7]",
            raw,
        )[0]

        name = clean_author_name(
            first_part
        )

        if (
            name
            and not re.search(
                r"\d",
                name,
            )
        ):
            return name

    return ""


def _author_from_meta(meta):
    for key in (
        "author",
        "article:author",
        "parsely-author",
        "dc.creator",
        "sailthru.author",
    ):
        names = [
            clean_author_name(value)
            for value in meta.get(
                key,
                [],
            )
        ]

        joined = _join_authors(
            names
        )

        if joined:
            return joined

    return ""


def extract_author(
    soup,
    meta,
    nodes,
):
    finders = (
        lambda: _author_from_json_ld(
            nodes
        ),
        lambda: _author_from_links(
            soup
        ),
        lambda: _author_from_byline(
            soup
        ),
        lambda: _author_from_meta(
            meta
        ),
    )

    for finder in finders:
        try:
            author = finder()
        except Exception:
            author = ""

        if author:
            return author

    return ""


def _class_segments(element):
    classes = (
        element.attrs or {}
    ).get("class")

    if isinstance(
        classes,
        str,
    ):
        classes = classes.split()

    if not isinstance(
        classes,
        list,
    ):
        return set()

    segments = set()

    for class_name in classes:
        if isinstance(
            class_name,
            str,
        ):
            for segment in re.split(
                r"__|--",
                class_name.lower(),
            ):
                if segment:
                    segments.add(segment)

    return segments


def is_noise_element(element):
    if element.name == "p":
        return bool(
            _class_segments(element)
            & P_NOISE_CLASS_TOKENS
        )

    if (
        element.name
        not in NOISE_CONTAINER_TAGS
    ):
        return False

    attributes = (
        element.attrs or {}
    )

    role = attributes.get(
        "role"
    )

    if (
        isinstance(role, str)
        and role.strip().lower()
        in NOISE_ROLES
    ):
        return True

    element_id = attributes.get(
        "id"
    )

    if (
        isinstance(element_id, str)
        and element_id.strip().lower()
        in NOISE_IDS
    ):
        return True

    return bool(
        _class_segments(element)
        & NOISE_CLASS_TOKENS
    )


def _inside_noise(element, root):
    for parent in element.parents:
        if parent is root:
            return False

        if (
            isinstance(parent, Tag)
            and is_noise_element(parent)
        ):
            return True

    return False


def _safe_decompose(element):
    try:
        if getattr(
            element,
            "decomposed",
            False,
        ):
            return

        element.decompose()

    except Exception:
        pass


def remove_hard_tags(
    root,
    strip_header,
):
    names = list(
        HARD_REMOVE_TAGS
    )

    if strip_header:
        names.append("header")

    for element in root.find_all(
        names
    ):
        _safe_decompose(
            element
        )


def prune_noise(root):
    candidates = [
        element
        for element in root.find_all(
            NOISE_CONTAINER_TAGS
            + ["p"]
        )
        if is_noise_element(element)
    ]

    if not candidates:
        return []

    candidate_ids = {
        id(element)
        for element in candidates
    }

    outermost = [
        element
        for element in candidates
        if not any(
            id(parent)
            in candidate_ids
            for parent in element.parents
        )
    ]

    total = len(
        normalize_text(
            root.get_text(" ")
        )
    )

    if total == 0:
        return []

    notes = []
    removable = []
    removed_size = 0

    for element in outermost:
        size = len(
            normalize_text(
                element.get_text(" ")
            )
        )

        if (
            size
            > total
            * MAX_SINGLE_PRUNE_FRACTION
        ):
            notes.append(
                "pruning_skipped_large_element"
            )
            continue

        removable.append(element)
        removed_size += size

    if (
        removed_size
        > total
        * MAX_TOTAL_PRUNE_FRACTION
    ):
        return [
            "pruning_skipped_too_aggressive"
        ]

    for element in removable:
        _safe_decompose(
            element
        )

    return notes


def collect_blocks(root):
    blocks = []

    for element in root.find_all(
        BLOCK_TAGS
    ):
        if (
            element.find_parent(
                "iframe"
            )
            is not None
        ):
            continue

        name = element.name

        if (
            name == "li"
            and element.find(
                [
                    "p",
                    "blockquote",
                    "h2",
                    "h3",
                    "h4",
                ]
            )
        ):
            continue

        if (
            name == "blockquote"
            and element.find(
                [
                    "p",
                    "li",
                    "blockquote",
                    "h2",
                    "h3",
                    "h4",
                ]
            )
        ):
            continue

        text = normalize_text(
            own_text(element)
        )

        if not text:
            continue

        if SKIP_BLOCK_RE.match(text):
            continue

        kind = (
            "h"
            if name in (
                "h2",
                "h3",
                "h4",
            )
            else "p"
        )

        blocks.append(
            (
                kind,
                text,
            )
        )

    return blocks


def dedupe_blocks(blocks):
    seen = set()
    unique_blocks = []

    for kind, text in blocks:
        if (
            kind == "p"
            and len(text)
            >= DEDUP_MIN_CHARS
        ):
            key = text.casefold()

            if key in seen:
                continue

            seen.add(key)

        unique_blocks.append(
            (
                kind,
                text,
            )
        )

    return unique_blocks


def is_tail_boilerplate(text):
    if len(text) > MAX_TAIL_BLOCK_CHARS:
        return False

    return any(
        pattern.search(text)
        for pattern in TAIL_BOILERPLATE_PATTERNS
    )


def trim_tail(blocks):
    blocks = list(blocks)

    removed = 0
    boilerplate_removed = False

    while (
        blocks
        and removed < MAX_TAIL_REMOVALS
    ):
        kind, text = blocks[-1]

        if (
            kind == "p"
            and is_tail_boilerplate(text)
        ):
            boilerplate_removed = True

        elif kind != "h":
            break

        blocks.pop()
        removed += 1

    return (
        blocks,
        boilerplate_removed,
    )


def build_clean_scope(
    element,
    strip_header=False,
):
    root = BeautifulSoup(
        str(element),
        "html.parser",
    )

    remove_hard_tags(
        root,
        strip_header,
    )

    notes = prune_noise(root)

    return root, notes


def extract_blocks(
    element,
    strip_header=False,
):
    root, notes = build_clean_scope(
        element,
        strip_header,
    )

    blocks = dedupe_blocks(
        collect_blocks(root)
    )

    blocks, boilerplate_removed = (
        trim_tail(blocks)
    )

    if boilerplate_removed:
        notes.append(
            "removed_tail_boilerplate"
        )

    return (
        blocks,
        notes,
        root,
    )


def is_valid_body(
    blocks,
    min_blocks,
):
    paragraphs = [
        text
        for kind, text in blocks
        if kind == "p"
    ]

    return (
        len(paragraphs)
        >= min_blocks
        and sum(
            len(text)
            for text in paragraphs
        )
        >= MIN_BODY_CHARS
    )


def iter_body_candidates(soup):
    primary = soup.select_one(
        "#content--body"
    )

    if primary is not None:
        yield (
            "#content--body",
            primary,
            1,
            False,
        )

    for element in soup.select(
        '[itemprop="articleBody"]'
    ):
        yield (
            '[itemprop="articleBody"]',
            element,
            1,
            False,
        )

    articles = [
        element
        for element in soup.find_all(
            "article"
        )
        if not _inside_noise(
            element,
            None,
        )
    ]

    articles.sort(
        key=lambda element: len(
            element.get_text()
        ),
        reverse=True,
    )

    for element in articles:
        yield (
            "article",
            element,
            3,
            True,
        )


def blocks_from_json_ld(nodes):
    body = json_ld_string(
        nodes,
        "articleBody",
    )

    if (
        not body
        or not body.strip()
    ):
        return [], None

    if re.search(
        r"</?(?:p|div|br|h[1-6]|"
        r"li|blockquote)\b",
        body,
        re.I,
    ):
        blocks, _, scope = (
            extract_blocks(
                BeautifulSoup(
                    body,
                    "html.parser",
                )
            )
        )

        return blocks, scope

    blocks = []

    for line in re.split(
        r"\n+",
        body,
    ):
        text = normalize_text(
            line
        )

        if text:
            blocks.append(
                ("p", text)
            )

    blocks = dedupe_blocks(
        blocks
    )

    blocks, _ = trim_tail(
        blocks
    )

    return blocks, None


def extract_article_body(
    soup,
    nodes,
    warnings,
):
    tried = []

    for (
        label,
        element,
        min_blocks,
        strip_header,
    ) in iter_body_candidates(
        soup
    ):
        if label not in tried:
            tried.append(label)

        blocks, notes, scope = (
            extract_blocks(
                element,
                strip_header,
            )
        )

        if is_valid_body(
            blocks,
            min_blocks,
        ):
            warnings.extend(
                notes
            )

            if label != "#content--body":
                warnings.append(
                    "body_fallback:"
                    + label
                )

            return (
                blocks,
                scope,
            )

    tried.append(
        "json-ld articleBody"
    )

    blocks, scope = (
        blocks_from_json_ld(nodes)
    )

    if is_valid_body(
        blocks,
        1,
    ):
        warnings.append(
            "body_fallback:json-ld"
        )

        return (
            blocks,
            scope,
        )

    raise ScrapeError(
        "could not extract a valid article "
        "body (tried: "
        + ", ".join(tried)
        + ")"
    )


def compose_text(
    blocks,
    standfirst,
):
    text = "\n\n".join(
        block_text
        for _, block_text in blocks
    )

    if (
        standfirst
        and standfirst.casefold()
        not in text.casefold()
    ):
        text = (
            standfirst
            + "\n\n"
            + text
        )

    return text


def best_srcset_url(srcset):
    candidates = []

    for index, entry in enumerate(
        re.split(
            r",\s*",
            srcset.strip(),
        )
    ):
        parts = entry.strip().split()

        if not parts:
            continue

        weight = 0.0

        if len(parts) > 1:
            descriptor = parts[1].lower()

            try:
                if descriptor.endswith("w"):
                    weight = float(
                        descriptor[:-1]
                    )

                elif descriptor.endswith("x"):
                    weight = (
                        float(
                            descriptor[:-1]
                        )
                        * 1000
                    )

            except ValueError:
                weight = 0.0

        candidates.append(
            (
                weight,
                index,
                parts[0],
            )
        )

    if not candidates:
        return ""

    reasonable = [
        item
        for item in candidates
        if item[0]
        <= MAX_REASONABLE_IMAGE_WIDTH
    ]

    if reasonable:
        return max(
            reasonable,
            key=lambda item: (
                item[0],
                item[1],
            ),
        )[2]

    return min(
        candidates,
        key=lambda item: (
            item[0],
            item[1],
        ),
    )[2]


def _image_source(image):
    for attribute in (
        "srcset",
        "data-srcset",
        "data-lazy-srcset",
    ):
        srcset = image.get(
            attribute
        )

        if (
            isinstance(srcset, str)
            and srcset.strip()
        ):
            candidate = best_srcset_url(
                srcset
            )

            if candidate:
                return candidate

    for attribute in (
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
    ):
        value = image.get(
            attribute
        )

        if (
            isinstance(value, str)
            and value.strip()
            and not value.strip()
            .lower()
            .startswith("data:")
        ):
            return value

    return ""


def _dimension(value):
    if (
        not isinstance(value, str)
        or "%"
        in value
    ):
        return None

    match = re.match(
        r"\s*(\d+)",
        value,
    )

    return (
        int(match.group(1))
        if match
        else None
    )


def _is_tiny_image(image):
    width = _dimension(
        image.get("width")
    )

    height = _dimension(
        image.get("height")
    )

    if (
        width is not None
        and width <= 2
    ):
        return True

    if (
        height is not None
        and height <= 2
    ):
        return True

    if (
        width is not None
        and height is not None
        and width < 50
        and height < 50
    ):
        return True

    return False


def _is_unwanted_image_url(url):
    path = urlparse(
        url
    ).path.lower()

    if TRACKING_IMAGE_RE.search(
        path
    ):
        return True

    if (
        path.endswith(".svg")
        and (
            "icon" in path
            or "logo" in path
        )
    ):
        return True

    return False


def _image_key(url):
    parsed = urlparse(url)

    if IMAGE_EXTENSION_RE.search(
        parsed.path
    ):
        return (
            parsed.netloc.lower()
            + parsed.path
        )

    return url


def extract_images(
    scope,
    meta,
    nodes,
    base_url,
):
    candidates = []

    open_graph_values = (
        meta.get("og:image", [])
        + meta.get(
            "og:image:secure_url",
            [],
        )
        + meta.get(
            "og:image:url",
            [],
        )
    )

    open_graph_images = [
        normalize_url(
            value,
            base_url,
        )
        for value in open_graph_values
    ]

    open_graph_images = [
        url
        for url in open_graph_images
        if url
    ]

    candidates.extend(
        open_graph_images
    )

    if not open_graph_images:
        for value in _urls_from_value(
            json_ld_get(
                nodes,
                "image",
            )
        ):
            url = normalize_url(
                value,
                base_url,
            )

            if url:
                candidates.append(
                    url
                )

    if scope is not None:
        for image in scope.find_all(
            "img"
        ):
            if _is_tiny_image(
                image
            ):
                continue

            url = normalize_url(
                _image_source(image),
                base_url,
            )

            if (
                url
                and not _is_unwanted_image_url(
                    url
                )
            ):
                candidates.append(
                    url
                )

    seen = set()
    images = []

    for url in candidates:
        key = _image_key(url)

        if key not in seen:
            seen.add(key)
            images.append(url)

    return images


def _is_video_host(url):
    host = (
        urlparse(url)
        .hostname
        or ""
    ).lower()

    return any(
        host == suffix
        or host.endswith(
            "." + suffix
        )
        for suffix in VIDEO_HOST_SUFFIXES
    )


def extract_videos(
    scope,
    meta,
    nodes,
    base_url,
):
    candidates = []

    for key in (
        "og:video",
        "og:video:url",
        "og:video:secure_url",
    ):
        for value in meta.get(
            key,
            [],
        ):
            url = normalize_url(
                value,
                base_url,
            )

            if url:
                candidates.append(
                    url
                )

    if scope is not None:
        for video in scope.find_all(
            "video"
        ):
            sources = [
                video.get("src")
            ]

            sources.extend(
                source.get("src")
                for source in video.find_all(
                    "source"
                )
            )

            for value in sources:
                url = normalize_url(
                    value,
                    base_url,
                )

                if url:
                    candidates.append(
                        url
                    )

        for iframe in scope.find_all(
            "iframe"
        ):
            value = (
                iframe.get("src")
                or iframe.get("data-src")
                or iframe.get(
                    "data-lazy-src"
                )
            )

            url = normalize_url(
                value,
                base_url,
            )

            if (
                url
                and _is_video_host(url)
            ):
                candidates.append(
                    url
                )

    article_node = (
        primary_article_node(
            nodes,
            base_url,
        )
    )

    if article_node is not None:
        for value in _urls_from_value(
            article_node.get(
                "video"
            )
        ):
            url = normalize_url(
                value,
                base_url,
            )

            if url:
                candidates.append(
                    url
                )

    seen = set()
    videos = []

    for url in candidates:
        if url not in seen:
            seen.add(url)
            videos.append(url)

    return videos


def _possible_paywall(
    meta,
    nodes,
):
    tier = meta_first(
        meta,
        "article:content_tier",
    ).casefold()

    if tier in (
        "locked",
        "metered",
    ):
        return True

    accessible = json_ld_get(
        nodes,
        "isAccessibleForFree",
    )

    return (
        accessible is False
        or (
            isinstance(
                accessible,
                str,
            )
            and accessible.strip()
            .lower()
            == "false"
        )
    )


def detect_page_type(
    url,
    title,
    heading,
    meta,
    nodes,
):
    path = urlparse(
        url
    ).path.lower()

    last_segment = (
        path.rstrip("/")
        .rsplit(
            "/",
            1,
        )[-1]
    )

    heading_texts = [
        title.casefold(),
        heading.casefold(),
    ]

    types = _all_node_types(
        nodes
    )

    og_type = meta_first(
        meta,
        "og:type",
    ).casefold()

    is_dated_article = bool(
        ARTICLE_PATH_RE.match(
            path
        )
    )

    if (
        path.startswith(
            (
                "/newsletter",
                "/newsletters",
            )
        )
        or last_segment.startswith(
            "the-download"
        )
        or any(
            NEWSLETTER_TITLE_RE.match(
                text
            )
            for text in heading_texts
        )
    ):
        return "newsletter"

    if (
        path.startswith(
            (
                "/podcast",
                "/podcasts",
            )
        )
        or (
            "podcastepisode"
            in types
            and not types
            & ARTICLE_TYPES
        )
    ):
        return "podcast"

    if (
        path.startswith(
            (
                "/video",
                "/videos",
            )
        )
        or (
            not is_dated_article
            and (
                og_type.startswith(
                    "video"
                )
                or (
                    "videoobject"
                    in types
                    and not types
                    & ARTICLE_TYPES
                )
            )
        )
    ):
        return "video"

    if any(
        segment
        in (
            "sponsored",
            "sponsored-content",
        )
        for segment in path.strip(
            "/"
        ).split("/")
    ):
        return "sponsored"

    return "article"


def _scrape(original_url):
    request_url = _validate_url(
        original_url
    )

    content, final_url = _fetch(
        request_url
    )

    soup = BeautifulSoup(
        content,
        "html.parser",
    )

    _check_not_blocked(
        soup,
        content,
        request_url,
        final_url,
    )

    meta = collect_meta(
        soup
    )

    nodes = load_json_ld(
        soup
    )

    title = extract_title(
        soup,
        meta,
        nodes,
    )

    heading = _first_h1_text(
        soup
    )

    page_type = detect_page_type(
        final_url,
        title,
        heading,
        meta,
        nodes,
    )

    author = extract_author(
        soup,
        meta,
        nodes,
    )

    published_at = (
        extract_published_at(
            soup,
            meta,
            nodes,
        )
    )

    standfirst = extract_standfirst(
        soup,
        meta,
        nodes,
        title,
    )

    if page_type in SKIPPED_PAGE_TYPES:
        result = _empty_result(
            original_url
        )

        result["page_type"] = (
            page_type
        )
        result["title"] = title
        result["author"] = author
        result["published_at"] = (
            published_at
        )
        result["standfirst"] = (
            standfirst
        )
        result["status"] = "skipped"

        return result

    warnings = []

    blocks, scope = (
        extract_article_body(
            soup,
            nodes,
            warnings,
        )
    )

    text = compose_text(
        blocks,
        standfirst,
    )

    if scope is None:
        article = soup.find(
            "article"
        )

        if article is not None:
            scope, _ = (
                build_clean_scope(
                    article,
                    True,
                )
            )

    images = extract_images(
        scope,
        meta,
        nodes,
        final_url,
    )

    videos = extract_videos(
        scope,
        meta,
        nodes,
        final_url,
    )

    main_image = (
        images[0]
        if images
        else ""
    )

    if not title:
        warnings.append(
            "missing_title"
        )

    if page_type == "sponsored":
        warnings.append(
            "sponsored_content"
        )

    if (
        len(text) < 2500
        and _possible_paywall(
            meta,
            nodes,
        )
    ):
        warnings.append(
            "possible_paywall"
        )

    result = {
        "page_type": page_type,
        "title": title,
        "text": text,
        "author": author,
        "published_at": published_at,
        "standfirst": standfirst,
        "main_image": main_image,
        "images": images,
        "videos": videos,
        "url": original_url,
        "status": "success",
    }

    if warnings:
        result["warnings"] = _unique(
            warnings
        )

    return result


def scrape(url):
    if isinstance(url, str):
        original_url = url
    elif url is None:
        original_url = ""
    else:
        original_url = str(url)

    try:
        return _scrape(
            original_url
        )

    except ScrapeError as error:
        return _error_result(
            original_url,
            str(error),
        )

    except Exception as error:
        return _error_result(
            original_url,
            "unexpected error: "
            + type(error).__name__
            + ": "
            + str(error),
        )
