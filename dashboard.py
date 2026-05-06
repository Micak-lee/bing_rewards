"""Rewards dashboard page object — points, login check, activity discovery."""
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page

from logger import get_logger

REWARDS_DASHBOARD_URL = "https://rewards.bing.com/"

# Selectors using stable attributes — update if Microsoft changes the dashboard
SELECTORS = {
    "login_button": "[data-bi-id='mecontrol']",
    "points_value": "[data-bi-id='points']",
    "daily_activity_card": "mee-card-group mee-card, [data-bi-id='daily'] a",
    "promo_link": ".promo_link, [data-bi-id*='promo']",
    "activity_card": "mee-card",
    "poll_option": "input[type='radio']",
    "quiz_option": "button[role='option'], .quiz-option",
    "more_activity_link": "a[href*='rewards.bing.com']",
    "claim_button": "button:has-text('Claim'), [data-bi-id*='claim']",
    "search_box": "#sb_form_q",
    "search_results": "#b_results",
}


@dataclass
class PointsInfo:
    """Current points breakdown."""
    available: int = 0
    today_earned: int = 0
    pc_searches_done: int = 0
    pc_searches_max: int = 150
    mobile_searches_done: int = 0
    mobile_searches_max: int = 100


@dataclass
class DailySet:
    """Represents the daily set of activities."""
    poll_url: Optional[str] = None
    quiz_urls: list[str] = field(default_factory=list)
    more_activities: list[dict] = field(default_factory=list)


class Dashboard:
    """Interacts with the Microsoft Rewards dashboard."""

    def __init__(self, page: Page):
        self._page = page
        self._log = get_logger()

    def navigate(self) -> bool:
        """Go to rewards dashboard. Returns False if redirected to login."""
        try:
            self._page.goto(
                REWARDS_DASHBOARD_URL,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            self._page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception as e:
            self._log.warning(f"Dashboard navigation timeout: {e}")

        current_url = self._page.url
        if "login.live.com" in current_url or "login.microsoftonline.com" in current_url:
            self._log.info("Redirected to login page")
            return False
        return True

    def get_points_info(self) -> PointsInfo:
        """Scrape current points and search progress from the dashboard."""
        info = PointsInfo()

        try:
            # Try to find points value in various possible locations
            points_text = self._safe_extract_text(
                "[data-bi-id='points']"
            ) or self._safe_extract_text(".points-value")

            if points_text:
                # Extract digits from string like "12,345 points"
                import re
                digits = re.sub(r"[^\d]", "", points_text)
                if digits:
                    info.available = int(digits)
        except Exception as e:
            self._log.warning(f"Failed to parse points: {e}")

        self._log.info(f"Current available points: {info.available}")
        return info

    def get_daily_set(self) -> DailySet:
        """Parse the dashboard to find today's available daily activities."""
        daily_set = DailySet()

        try:
            # Click on the daily set section if it exists
            self._page.wait_for_selector("mee-card", timeout=15_000)

            # Find all activity links/cards
            links = self._page.query_selector_all("a[href*='rewards.bing.com']")

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.inner_text().strip().lower()

                    if not text or not href:
                        continue

                    # Classify the activity by its text content
                    if any(kw in text for kw in ["poll", "投票", "survey", "调查"]):
                        if not daily_set.poll_url:
                            daily_set.poll_url = href
                            self._log.info(f"Found poll: {text[:50]}")
                    elif any(kw in text for kw in ["quiz", "测验", "trivia", "question", "问题", "this or that", "supersonic", "lightning"]):
                        if href not in daily_set.quiz_urls:
                            daily_set.quiz_urls.append(href)
                            self._log.info(f"Found quiz: {text[:50]}")
                    else:
                        # More activities
                        daily_set.more_activities.append({
                            "title": text[:100],
                            "url": href,
                        })
                        self._log.info(f"Found activity: {text[:50]}")

                except Exception:
                    continue

        except Exception as e:
            self._log.warning(f"Daily set discovery failed: {e}")

        self._log.info(
            f"Daily set: poll={bool(daily_set.poll_url)}, "
            f"quizzes={len(daily_set.quiz_urls)}, "
            f"more_activities={len(daily_set.more_activities)}"
        )
        return daily_set

    def _safe_extract_text(self, selector: str, default: str = "") -> str:
        """Extract text from an element, returning default on failure."""
        try:
            el = self._page.query_selector(selector)
            return el.inner_text().strip() if el else default
        except Exception:
            return default
