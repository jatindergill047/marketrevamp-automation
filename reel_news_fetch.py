"""Bounded HTTPS source extraction for optional Reel reviews only.

Keep the production carousel's existing fetcher unchanged. Article snippets are
never invented: only publisher HTML passed through Trafilatura is eligible.
"""
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_ARTICLE_ATTEMPTS = 40
ARTICLE_TIMEOUT_SECONDS = 7
MAX_HTML_BYTES = 1_000_000


def fetch_reel_article(url, *, opener=urlopen):
    if not isinstance(url, str):
        return ""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ""
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MarketRevampNewsCollector/1.0)",
        "Accept": "text/html,application/xhtml+xml;q=0.9",
    })
    try:
        with opener(req, timeout=ARTICLE_TIMEOUT_SECONDS) as response:
            final = urlsplit(response.geturl())
            original_host = parsed.hostname.lower().removeprefix("www.")
            destination_host = (final.hostname or "").lower().removeprefix("www.")
            if final.scheme != "https" or destination_host != original_host:
                print("Reel article redirect switched publisher: skipped")
                return ""
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                return ""
            content = response.read(MAX_HTML_BYTES + 1)
        if not content or len(content) > MAX_HTML_BYTES:
            return ""
        import trafilatura
        text = trafilatura.extract(
            content, include_comments=False, include_tables=False,
            favor_precision=True,
        )
        return (text or "")[:12000]
    except Exception as exc:
        print(f"Reel article unavailable within bounded fetch: {type(exc).__name__}")
        return ""


def limited_article_extractor(*, max_attempts=MAX_ARTICLE_ATTEMPTS,
                              fetcher=fetch_reel_article):
    """Conserve GitHub runner time and refuse incomplete Reels instead of hanging."""
    if not 1 <= max_attempts <= 40:
        raise ValueError("Reel article fetch cap must be 1–40")
    count = 0

    def extract(url):
        nonlocal count
        if count >= max_attempts:
            return ""
        count += 1
        return fetcher(url)
    return extract
