"""Bing search automation for earning search points."""
import random
import time
from urllib.parse import quote

from playwright.sync_api import Page

from config import Config
from logger import get_logger
from utils import human_delay, retry

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36 EdgA/120.0.0.0"
)


class SearchEngine:
    """Performs automated Bing searches to earn Rewards points."""

    def __init__(self, page: Page, config: Config):
        self._page = page
        self._config = config.search
        self._behavior = config.behavior
        self._log = get_logger()

    def search(self, query: str, timeout: int = 15_000) -> bool:
        """Execute a single Bing search via URL navigation.

        Returns True if the search completed successfully (results loaded).
        """
        encoded = quote(query)
        url = f"{self._config.search_base_url}?q={encoded}&form=QBRE"

        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Wait for results container
            self._page.wait_for_selector("#b_results", state="attached", timeout=timeout)
            self._log.debug(f"Searched: '{query}'")
            return True
        except Exception as e:
            self._log.warning(f"Search failed for '{query}': {e}")
            return False

    def do_pc_searches(self, queries: list[str]) -> int:
        """Run a batch of PC searches using the default desktop user agent.

        Returns the number of successful searches.
        """
        self._log.info(f"Starting {len(queries)} PC searches...")
        success = 0

        for i, query in enumerate(queries, 1):
            if self.search(query):
                success += 1

            if i % 5 == 0:
                self._log.info(f"PC search progress: {i}/{len(queries)}")

            if i < len(queries):
                delay = random.uniform(
                    self._config.min_delay, self._config.max_delay
                )
                self._log.debug(f"Waiting {delay:.1f}s before next search...")
                time.sleep(delay)

        self._log.info(f"PC searches completed: {success}/{len(queries)}")
        return success

    def do_mobile_searches(self, queries: list[str]) -> int:
        """Run a batch of mobile searches by spoofing mobile User-Agent.

        Uses page.route() to intercept requests and inject a mobile UA header,
        combined with a mobile viewport size. This preserves the persistent
        context's cookies so the user remains logged in.

        Returns the number of successful searches.
        """
        self._log.info(f"Starting {len(queries)} mobile searches...")

        # Save original viewport
        original_viewport = self._page.viewport_size

        # Set mobile viewport
        self._page.set_viewport_size({"width": 390, "height": 844})

        # Intercept requests to add mobile UA
        def route_intercept(route):
            headers = {**route.request.headers}
            headers["user-agent"] = MOBILE_USER_AGENT
            route.continue_(headers=headers)

        self._page.route("**/*", route_intercept)

        success = 0
        try:
            for i, query in enumerate(queries, 1):
                if self.search(query):
                    success += 1

                if i % 5 == 0:
                    self._log.info(f"Mobile search progress: {i}/{len(queries)}")

                if i < len(queries):
                    delay = random.uniform(
                        self._config.min_delay, self._config.max_delay
                    )
                    time.sleep(delay)
        finally:
            # Clean up: remove route interceptor and restore viewport
            self._page.unroute("**/*", route_intercept)
            if original_viewport:
                self._page.set_viewport_size(original_viewport)

        self._log.info(f"Mobile searches completed: {success}/{len(queries)}")
        return success
