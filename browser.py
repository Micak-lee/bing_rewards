"""Playwright browser lifecycle with persistent context for login state."""
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    BrowserContext,
    Page,
    Playwright,
)

from config import Config
from logger import get_logger

USER_DATA_DIR = Path.home() / ".msrewards_browser_data"

# Anti-detection: scripts injected into every page to hide automation traits
ANTI_DETECTION_SCRIPT = """
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Fake plugins array — real browsers have plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});

// Remove automation-related properties
delete window.__playwright;
delete window.__pw_manual;
delete window.__PW_inspect;

// Override chrome.runtime if present
if (window.chrome && window.chrome.runtime) {
    // Keep normal chrome.runtime
} else {
    window.chrome = { runtime: {} };
}

// Fix permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);

// Override headless detection
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""


class BrowserManager:
    """Manages Playwright browser lifecycle with persistent login state.

    Uses launch_persistent_context so cookies, localStorage, and session
    data persist in ~/.msrewards_browser_data across runs.
    """

    def __init__(self, config: Config):
        self._config = config
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._log = get_logger()

    def launch(self) -> BrowserContext:
        """Launch browser with persistent context.

        Tries system Edge first (channel="msedge"), falls back to bundled Chromium.
        """
        self._log.info("Starting Playwright browser...")
        self._playwright = sync_playwright().start()

        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        channel = self._config.browser.channel
        headless = self._config.browser.headless
        viewport = {
            "width": self._config.browser.viewport_width,
            "height": self._config.browser.viewport_height,
        }

        # Flags to suppress the "automated software" banner and reduce detection
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=AutomationControlled",
            "--disable-component-update",
            "--disable-default-apps",
            "--no-default-browser-check",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
        ]

        try:
            if channel:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(USER_DATA_DIR),
                    channel=channel,
                    headless=headless,
                    viewport=viewport,
                    locale=self._config.browser.locale,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                )
            else:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(USER_DATA_DIR),
                    headless=headless,
                    viewport=viewport,
                    locale=self._config.browser.locale,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                )
        except Exception as e:
            self._log.warning(f"Failed to launch with channel='{channel}': {e}")
            self._log.info("Falling back to bundled Chromium...")
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                headless=headless,
                viewport=viewport,
                locale=self._config.browser.locale,
                args=launch_args,
                ignore_default_args=["--enable-automation"],
            )

        self._log.info("Browser launched successfully")
        return self._context

    def new_page(self) -> Page:
        """Create a new page with anti-detection scripts injected.

        Falls back to reusing an existing page if browser refuses new tabs.
        """
        if not self._context:
            raise RuntimeError("Browser not launched. Call launch() first.")

        try:
            page = self._context.new_page()
        except Exception as e:
            self._log.warning(f"new_page() failed ({e}), reusing existing page")
            pages = self._context.pages
            if pages:
                page = pages[-1]
            else:
                raise RuntimeError("No pages available in browser context")

        page.add_init_script(ANTI_DETECTION_SCRIPT)
        return page

    def is_logged_in(self, page: Page) -> bool:
        """Check if currently authenticated by visiting rewards dashboard."""
        try:
            page.goto(
                "https://rewards.bing.com/",
                wait_until="domcontentloaded",
                timeout=15_000,
            )
            current_url = page.url
            if "login.live.com" in current_url or "login.microsoftonline.com" in current_url:
                return False
            return True
        except Exception:
            return False

    def save_auth_state(self, path: Path) -> None:
        """Export auth state to JSON as backup."""
        if self._context:
            self._context.storage_state(path=str(path))
            self._log.info(f"Auth state saved to {path}")

    def close(self) -> None:
        """Gracefully close browser and stop playwright."""
        if self._config.behavior.save_state_on_exit and self._context:
            self.save_auth_state(Path(self._config.behavior.state_file))
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()
        self._log.info("Browser closed")
