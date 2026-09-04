"""Fetch today's hot/trending search queries from Bing or Baidu.

Uses real trending topics as search queries for more natural-looking Bing searches.
"""
import json
import re
import urllib.parse
import urllib.request
from typing import Optional
from logger import get_logger


def _fetch_json(url: str, headers: dict | None = None,
                timeout: int = 10) -> Optional[str]:
    """Fetch URL content with proper headers."""
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


# ── Baidu Hot Search ──────────────────────────────────────────

BAIDU_API_URL = "https://top.baidu.com/api/board?tab=realtime"


def fetch_baidu_hot(max_count: int = 30) -> list[str]:
    """Fetch hot search terms from Baidu's realtime hot board API.

    Returns a list of hot search query strings, up to max_count.
    """
    log = get_logger()
    log.info("Fetching Baidu hot searches...")

    try:
        data = _fetch_json(BAIDU_API_URL)
        if not data:
            log.warning("Baidu API returned no data")
            return []

        parsed = json.loads(data)
        cards = (
            parsed.get("data", {})
            .get("cards", [])
        )
        queries = []
        for card in cards:
            for item in card.get("content", []):
                word = (item.get("word", "") or "").strip()
                if word and len(word) > 1:
                    queries.append(word)
                    if len(queries) >= max_count:
                        break
            if len(queries) >= max_count:
                break

        if queries:
            log.info(f"Got {len(queries)} Baidu hot searches")
            return queries

    except Exception as e:
        log.warning(f"Baidu hot search failed: {e}")

    return []


BAIDU_HTML_URL = "https://top.baidu.com/board?tab=realtime"


def fetch_baidu_hot_html(max_count: int = 30) -> list[str]:
    """Fallback: scrape hot search terms from Baidu's HTML page."""
    log = get_logger()

    html = _fetch_json(BAIDU_HTML_URL, timeout=15)
    if not html:
        return []

    queries = []
    # Try to find hot search words in the HTML
    # Pattern 1: JSON embedded in script tags
    for match in re.finditer(r'"word"\s*:\s*"([^"]+)"', html):
        word = match.group(1)
        if word and len(word) > 1 and word not in queries:
            queries.append(word)
            if len(queries) >= max_count:
                break

    # Pattern 2: look for keyword in HTML data attributes
    if len(queries) < 5:
        for match in re.finditer(r'data-word="([^"]+)"', html):
            word = match.group(1)
            if word and word not in queries:
                queries.append(word)
                if len(queries) >= max_count:
                    break

    if queries:
        log.info(f"Got {len(queries)} Baidu hot searches (HTML fallback)")
    return queries


# ── Bing Trending ──────────────────────────────────────────────

BING_HOMEPAGE_URL = "https://www.bing.com"
BING_HOMEPAGE_CN_URL = "https://www.bing.com/?cc=cn"


def fetch_bing_trending(max_count: int = 30) -> list[str]:
    """Fetch trending searches from Bing homepage.

    Bing shows trending/search suggestions on its homepage and
    also in search results. We parse the homepage HTML.
    """
    log = get_logger()
    log.info("Fetching Bing trending searches...")

    html = _fetch_json(BING_HOMEPAGE_URL, timeout=15)
    if not html:
        log.warning("Bing homepage returned no data")
        return []

    queries = []

    # Pattern 1: Popular search suggestions embedded in JSON-LD or script
    for match in re.finditer(
        r'"popular searches[^}]*?"text"\s*:\s*"([^"]+)"',
        html, re.IGNORECASE,
    ):
        word = match.group(1).strip()
        if word and word not in queries:
            queries.append(word)
            if len(queries) >= max_count:
                break

    # Pattern 2: Look for search suggestion data attributes
    if len(queries) < 5:
        for match in re.finditer(
            r'suggestion="([^"]+)"',
            html,
        ):
            word = match.group(1).strip()
            if word and word not in queries:
                queries.append(word)
                if len(queries) >= max_count:
                    break

    # Pattern 3: Text in trending-now elements
    if len(queries) < 5:
        for match in re.finditer(r'title="([^"]*?)"\s*class="[^"]*?trend', html):
            word = match.group(1).strip()
            if word and len(word) > 1 and word not in queries:
                queries.append(word)
                if len(queries) >= max_count:
                    break

    if queries:
        log.info(f"Got {len(queries)} Bing trending searches")
    else:
        log.info("No Bing trending found, falling back to Baidu...")

    return queries


# ── Unified Interface ─────────────────────────────────────────

def fetch_hot_searches(source: str = "auto", max_count: int = 30) -> list[str]:
    """Fetch hot/trending search queries from the best available source.

    Args:
        source: "bing", "baidu", or "auto" (try bing then baidu)
        max_count: Maximum number of queries to return

    Returns:
        List of hot search query strings
    """
    if source == "bing":
        queries = fetch_bing_trending(max_count)
    elif source == "baidu":
        queries = fetch_baidu_hot(max_count)
    else:
        # Auto: try Bing first, fallback to Baidu
        queries = fetch_bing_trending(max_count)
        if not queries:
            queries = fetch_baidu_hot(max_count)
        if not queries:
            queries = fetch_baidu_hot_html(max_count)

    log = get_logger()
    if queries:
        log.info(f"Total hot searches obtained: {len(queries)}")
        for i, q in enumerate(queries[:10], 1):
            log.debug(f"  [{i}] {q}")
        return queries

    log.warning("No hot searches found from any source")
    return []


def get_search_config_hint() -> str:
    """Return a config value hint for query_language based on hot search source."""
    return "zh"  # Hot searches from both Baidu and Bing CN are primarily Chinese
