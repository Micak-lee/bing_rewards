"""
Microsoft Rewards Auto-Farming Tool

Automates earning Microsoft Rewards points via:
  1. Bing PC searches
  2. Bing mobile searches (UA spoofing)
  3. Daily activities (poll, quiz, more activities)

Usage:
  python main.py

First run: browser opens, log into your Microsoft account, press ENTER.
Subsequent runs: auto-login via persistent browser data in ~/.msrewards_browser_data/
"""
import sys
from pathlib import Path

from config import load_config, Config
from logger import setup_logger, get_logger
from browser import BrowserManager
from queries import QueryGenerator
from search import SearchEngine
from dashboard import Dashboard
from activities import ActivityHandler


def ensure_login(dashboard: Dashboard, browser_manager: BrowserManager) -> bool:
    """Check login status. If not logged in, prompt user to log in manually.

    Returns True once logged in, False if user wants to quit.
    """
    log = get_logger()

    if dashboard.navigate():
        log.info("Already logged in")
        return True

    log.info("=" * 60)
    log.info("NOT LOGGED IN — Please log into your Microsoft account")
    log.info("The browser window is visible. Log in manually, then press ENTER.")
    log.info("=" * 60)

    try:
        input(">>> Press ENTER after logging in (or Ctrl+C to quit): ")
    except (KeyboardInterrupt, EOFError):
        return False

    # Re-check login
    if dashboard.navigate():
        log.info("Login confirmed")
        return True

    log.error("Login still not detected. Please try again.")
    return False


def print_banner() -> None:
    """Print startup banner."""
    banner = r"""
╔══════════════════════════════════════════╗
║     Microsoft Rewards Auto-Farming       ║
║        Bing Search + Daily Activities     ║
╚══════════════════════════════════════════╝
"""
    print(banner)


def main() -> None:
    """Main entry point."""
    print_banner()

    # 1. Load configuration
    config = load_config(Path("config.yaml"))

    # 2. Setup logging
    log = setup_logger(config.behavior.log_level)
    log.info("Starting Microsoft Rewards Auto-Farming")

    # 3. Load query banks
    log.info("Loading search keywords...")
    qg = QueryGenerator.from_files()
    log.info(
        f"Loaded {len(qg.zh_keywords)} Chinese + {len(qg.en_keywords)} English keywords"
    )

    # 4. Launch browser
    bm = BrowserManager(config)
    bm.launch()
    page = bm.new_page()

    try:
        # 5. Dashboard + login check
        dash = Dashboard(page)
        if not ensure_login(dash, bm):
            log.error("Cannot proceed without login. Exiting.")
            sys.exit(1)

        # 6. Read current state
        points_before = dash.get_points_info()
        daily_set = dash.get_daily_set()

        # 7. PC searches
        search_handler = SearchEngine(page, config)
        if config.search.pc_count > 0:
            pc_queries = qg.generate_batch(
                config.search.pc_count, config.search.query_language
            )
            pc_done = search_handler.do_pc_searches(pc_queries)
            log.info(f"PC searches: {pc_done}/{config.search.pc_count} successful")
        else:
            log.info("PC searches disabled (count=0)")

        # 8. Mobile searches
        if config.search.mobile_count > 0:
            mobile_queries = qg.generate_batch(
                config.search.mobile_count, config.search.query_language
            )
            mobile_done = search_handler.do_mobile_searches(mobile_queries)
            log.info(
                f"Mobile searches: {mobile_done}/{config.search.mobile_count} successful"
            )
        else:
            log.info("Mobile searches disabled (count=0)")

        # 9. Daily activities
        activity_results = {"poll": False, "quizzes": 0, "more": 0}
        if config.activities.enabled and (
            daily_set.poll_url
            or daily_set.quiz_urls
            or daily_set.more_activities
        ):
            handler = ActivityHandler(page, config)
            activity_results = handler.run_all(daily_set)
            log.info(
                f"Activities: poll={'OK' if activity_results['poll'] else 'NO'}, "
                f"quizzes={activity_results['quizzes']}, "
                f"more={activity_results['more']}"
            )
        else:
            log.info("No activities available or activities disabled")

        # 10. Report final points
        dash.navigate()
        points_after = dash.get_points_info()
        earned = points_after.available - points_before.available
        task_summary = (
            f"PC searches={pc_done if config.search.pc_count > 0 else 'skipped'}, "
            f"Mobile searches={mobile_done if config.search.mobile_count > 0 else 'skipped'}, "
            f"Poll={'OK' if activity_results['poll'] else 'N/A'}, "
            f"Quizzes={activity_results['quizzes']}, "
            f"More={activity_results['more']}"
        )
        log.info("=" * 60)
        log.info(f"POINTS EARNED THIS SESSION: {earned}")
        log.info(f"TOTAL POINTS: {points_after.available}")
        log.info(f"TASKS: {task_summary}")
        log.info("=" * 60)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.exception(f"Unexpected error: {e}")
    finally:
        bm.close()
        log.info("Session ended")


if __name__ == "__main__":
    main()
