"""Daily activities automation — poll, quiz, and more-activities handlers."""
import random
import re
import time
from urllib.parse import quote

from playwright.sync_api import Page

from config import Config
from dashboard import DailySet
from logger import get_logger
from utils import human_delay


class ActivityHandler:
    """Handles all Microsoft Rewards daily activity types.

    Three activity types:
      1. Daily Poll — single multiple-choice question
      2. Quizzes — multi-question (standard, This-or-That, Lightning, Supersonic)
      3. More Activities — simple click-through links
    """

    def __init__(self, page: Page, config: Config):
        self._page = page
        self._config = config.activities
        self._search_config = config.search
        self._log = get_logger()

    def run_all(self, daily_set: DailySet) -> dict:
        """Execute all available daily activities."""
        results = {"poll": False, "quizzes": 0, "more": 0}

        # 1. Poll
        if daily_set.poll_url:
            self._log.info("Handling daily poll...")
            results["poll"] = self.handle_poll(daily_set.poll_url)
        else:
            self._log.info("No poll found — may already be completed")

        # 2. Quizzes
        for quiz_url in daily_set.quiz_urls:
            self._log.info(f"Handling quiz: {quiz_url[:80]}...")
            if self.handle_quiz(quiz_url):
                results["quizzes"] += 1

        # 3. More Activities
        if daily_set.more_activities:
            self._log.info(
                f"Handling {len(daily_set.more_activities)} more activities..."
            )
            results["more"] = self.handle_more_activities(
                daily_set.more_activities
            )

        return results

    # ---- Poll ----

    def handle_poll(self, poll_url: str) -> bool:
        """Complete the daily poll by selecting a random option."""
        try:
            self._page.goto(poll_url, wait_until="domcontentloaded", timeout=20_000)
            self._page.wait_for_load_state("networkidle", timeout=10_000)

            # Find radio buttons or clickable options
            options = self._page.query_selector_all("input[type='radio']")
            if not options:
                options = self._page.query_selector_all(
                    "button[role='radio'], [aria-role='radio'], .poll-option"
                )

            if not options:
                self._log.warning("No poll options found")
                return False

            # Select an option based on config
            choice = self._config.poll_choice
            if choice == "first":
                selected = options[0]
            elif choice == "last":
                selected = options[-1]
            else:
                selected = random.choice(options)

            selected.click()
            human_delay(1, 2)

            # Click submit/confirm button if present
            submit_btn = self._page.query_selector(
                "button:has-text('Submit'), button:has-text('提交'), "
                "button:has-text('Vote'), button:has-text('投票'), "
                "button:has-text('Confirm'), button:has-text('确认'), "
                "[data-bi-id*='submit']"
            )
            if submit_btn:
                submit_btn.click()
                human_delay(2, 4)

            self._log.info("Poll completed")
            return True

        except Exception as e:
            self._log.warning(f"Poll failed: {e}")
            return False

    # ---- Quiz ----

    def handle_quiz(self, quiz_url: str) -> bool:
        """Complete a quiz using Bing search to find answers.

        Strategy:
        1. Navigate to quiz
        2. Detect quiz type from DOM
        3. For each question: read text, search Bing, select best answer
        4. Handle retries on wrong answers
        """
        try:
            self._page.goto(quiz_url, wait_until="domcontentloaded", timeout=20_000)
            self._page.wait_for_load_state("networkidle", timeout=10_000)

            max_questions = 10  # upper bound
            for q_idx in range(max_questions):
                if not self._process_quiz_question(q_idx):
                    break  # no more questions or quiz finished

            # Check for final "claim points" or "done" button
            self._click_if_exists(
                "button:has-text('Claim'), button:has-text('Done'), "
                "button:has-text('完成'), button:has-text('领取')",
                timeout=5_000,
            )
            human_delay(1, 3)

            self._log.info("Quiz completed")
            return True

        except Exception as e:
            self._log.warning(f"Quiz failed: {e}")
            return False

    def _process_quiz_question(self, q_idx: int) -> bool:
        """Process a single quiz question. Returns False if no more questions."""
        human_delay(self._config.quiz_search_delay - 1, self._config.quiz_search_delay)

        # Read question text
        question_text = self._get_question_text()
        if not question_text:
            self._log.debug(f"No question text found at question {q_idx + 1}")
            return False

        self._log.debug(f"Question {q_idx + 1}: {question_text[:80]}")

        # Find the answer via Bing search
        answer = self._search_for_answer(question_text)
        if not answer:
            # Fallback: pick a random option
            self._log.debug("No answer found, picking random option")
            answer = "__random__"

        # Select the answer in the quiz UI
        return self._select_answer(answer, q_idx)

    def _get_question_text(self) -> str:
        """Extract the current question text from the quiz page."""
        # Try multiple possible selectors for question text
        selectors = [
            ".quiz-question",
            ".question-text",
            "[data-bi-id*='question']",
            ".bt_poll",
            "h2",
            "h3",
            ".rqTitle",
            ".mainQuestion",
        ]
        for sel in selectors:
            el = self._page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text and len(text) > 3:
                    return text
        return ""

    def _search_for_answer(self, question: str) -> str | None:
        """Search Bing for the question text and try to extract an answer.

        Opens a new tab for the search to keep quiz state intact.
        """
        try:
            page = self._page.context.new_page()
            try:
                encoded = quote(question[:200])
                search_url = f"{self._search_config.search_base_url}?q={encoded}"
                page.goto(search_url, wait_until="domcontentloaded", timeout=15_000)
                page.wait_for_selector("#b_results", timeout=10_000)
                human_delay(1, 2)

                # Try to extract answer from search results
                answer = self._extract_answer_from_serp(page)
                return answer
            finally:
                page.close()
        except Exception as e:
            self._log.debug(f"Answer search failed: {e}")
            return None

    def _extract_answer_from_serp(self, page: Page) -> str | None:
        """Parse Bing SERP to extract a likely answer.

        Priority:
        1. Featured snippet / knowledge panel
        2. Top result snippet
        3. Bold text in results
        """
        # 1. Featured snippet or knowledge panel
        snippet_selectors = [
            ".b_ans",           # Answer box
            ".b_factrow",       # Fact row
            ".b_snippet",       # Featured snippet
            ".b_entityTP",      # Entity panel
            "[data-tag*='snippet']",
        ]
        for sel in snippet_selectors:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text and len(text) > 2:
                    return text[:200]

        # 2. Top result snippet text
        result_texts = []
        snippet_els = page.query_selector_all(".b_caption p, .b_lineclamp2, .b_algoSlug")
        for el in snippet_els[:3]:
            text = el.inner_text().strip()
            if text and len(text) > 5:
                result_texts.append(text)

        # 3. Bold/highlighted text
        bold_els = page.query_selector_all("#b_results strong, #b_results b")
        for el in bold_els[:5]:
            text = el.inner_text().strip()
            if text and len(text) > 1:
                result_texts.append(text)

        if result_texts:
            # Return the longest meaningful snippet
            return max(result_texts, key=len)

        return None

    def _select_answer(self, answer: str, q_idx: int) -> bool:
        """Click the answer option in the quiz UI.

        If answer is a snippet, try to match it against available options.
        """
        # Find clickable answer options
        options = self._page.query_selector_all(
            "button[role='option'], [data-bi-id*='option'], "
            ".quiz-option, .mc-option, button.option, "
            "input[type='radio'] + label, .option-label"
        )
        if not options:
            # Try clicking anywhere on option cards
            options = self._page.query_selector_all(
                "[data-bi-id*='quiz'] button, .bt_poll button, "
                ".rqOption, .quizOption, [aria-label]"
            )

        if not options:
            self._log.debug("No clickable options found")
            return False

        # Filter out non-answer buttons (next, submit, etc.)
        valid_options = [
            o for o in options
            if o.is_visible() and not any(
                kw in (o.inner_text().lower() or "")
                for kw in ["next", "submit", "完成", "下一个", "提交"]
            )
        ]
        if not valid_options:
            valid_options = [o for o in options if o.is_visible()]

        if not valid_options:
            return False

        # Try to find the best matching option
        if answer and answer != "__random__":
            best = self._best_match(answer, valid_options)
        else:
            best = random.choice(valid_options)

        try:
            best.click()
            human_delay(1.5, 3)

            # Check if there's feedback (correct/wrong) and handle retry
            self._handle_quiz_feedback(valid_options)

            # Click "Next" if this isn't the last question
            self._click_if_exists(
                "button:has-text('Next'), button:has-text('下一个'), "
                "[data-bi-id*='next']",
                timeout=3_000,
            )

            return True
        except Exception as e:
            self._log.debug(f"Failed to click option: {e}")
            return False

    def _best_match(self, answer: str, options: list) -> any:
        """Find the option whose text best matches the answer snippet."""
        answer_lower = answer.lower()
        scored = []

        for opt in options:
            text = (opt.inner_text() or "").strip().lower()
            if not text:
                scored.append((0, opt))
                continue

            score = 0
            # Count word overlaps
            answer_words = set(answer_lower.split())
            text_words = set(text.split())
            overlap = answer_words & text_words
            score += len(overlap) * 10

            # Bonus for exact substring match
            if text in answer_lower or answer_lower in text:
                score += 50

            # Bonus for being a short, direct match
            if len(text) < 100 and len(overlap) >= 1:
                score += 20

            scored.append((score, opt))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else random.choice(options)

    def _handle_quiz_feedback(self, options: list) -> None:
        """Check if answer was wrong and retry if configured."""
        for attempt in range(self._config.max_quiz_retries):
            time.sleep(1.5)
            # Check for "wrong" indicators
            wrong = self._page.query_selector(
                "[data-bi-id*='wrong'], [data-bi-id*='incorrect'], "
                ".wrong, .incorrect, .rqWrongAnswer"
            )
            if not wrong:
                break  # Correct answer or no feedback yet

            # Try remaining options
            remaining = [o for o in options if o.is_visible()]
            if len(remaining) <= 1:
                break
            random.choice(remaining).click()

    # ---- More Activities ----

    def handle_more_activities(self, activities: list[dict]) -> int:
        """Process 'More Activities' click-through items.

        Each item opens a new tab, may require scrolling or clicking a claim button.
        Returns count of completed activities.
        """
        completed = 0

        for activity in activities:
            try:
                self._log.debug(f"Processing activity: {activity.get('title', '')[:50]}")

                # Click the activity link (may open new tab)
                self._page.goto(activity["url"], wait_until="domcontentloaded", timeout=20_000)
                self._page.wait_for_load_state("networkidle", timeout=self._config.more_activities_timeout * 1000)

                # Look for a "claim points" or similar button
                self._click_if_exists(
                    "button:has-text('Claim'), button:has-text('领取'), "
                    "button:has-text('Earn'), button:has-text('Get points'), "
                    "[data-bi-id*='claim'], [data-bi-id*='earn']",
                    timeout=8_000,
                )

                human_delay(2, 5)
                completed += 1

            except Exception as e:
                self._log.warning(f"Activity failed: {e}")
                continue

        self._log.info(f"More activities completed: {completed}/{len(activities)}")
        return completed

    # ---- Helpers ----

    def _click_if_exists(self, selector: str, timeout: int = 5_000) -> bool:
        """Click an element if it appears within the timeout."""
        try:
            el = self._page.wait_for_selector(
                selector, state="visible", timeout=timeout
            )
            if el:
                el.click()
                return True
        except Exception:
            pass
        return False
