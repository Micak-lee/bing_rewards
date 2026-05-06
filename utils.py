"""Utility functions: timing, retries, safe DOM interactions."""
import random
import time
import functools
from pathlib import Path
from typing import Callable, TypeVar

from playwright.sync_api import Page

F = TypeVar("F", bound=Callable)


def human_delay(min_s: float = 0.5, max_s: float = 3.0) -> None:
    """Random delay to simulate human pauses."""
    time.sleep(random.uniform(min_s, max_s))


def retry(
    max_attempts: int = 3,
    delay: float = 5.0,
    exceptions: tuple = (Exception,),
):
    """Decorator: retry a function on failure with exponential backoff."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        wait = delay * (2 ** (attempt - 1))
                        time.sleep(wait)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def safe_click(page: Page, selector: str, timeout: int = 10_000) -> bool:
    """Click an element if visible. Returns True on success."""
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
        page.click(selector)
        return True
    except Exception:
        return False


def safe_get_text(page: Page, selector: str, default: str = "") -> str:
    """Extract text from an element, returning default on failure."""
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else default
    except Exception:
        return default


def take_screenshot(page: Page, name: str) -> None:
    """Save a debug screenshot to the screenshots directory."""
    import datetime

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path("screenshots")
    path.mkdir(exist_ok=True)
    filepath = path / f"{stamp}_{name}.png"
    page.screenshot(path=str(filepath))
