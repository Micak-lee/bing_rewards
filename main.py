"""
Microsoft Rewards Auto-Farming Tool

Automates earning Microsoft Rewards points via:
  1. Bing PC searches
  2. Bing mobile searches (UA spoofing)
  3. Daily activities (poll, quiz, more activities)
  4. Bing mobile app "Read to Earn" via ADB phone connection

Usage:
  python main.py                    # 完整流程（搜索 + 活动 + 阅读）
  python main.py --read-only        # 仅执行手机"阅读以赚取"
  python main.py --no-read          # 跳过"阅读以赚取"，只做搜索+活动

First run: browser opens, log into your Microsoft account, press ENTER.
Phone setup: run `python phone_setup.py` first to check ADB connection.
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
from mobile_app import AndroidEmulator


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


def prompt_search_counts(config: Config) -> tuple[int, int]:
    """Prompt user for PC and mobile search counts.

    Returns (pc_count, mobile_count). User can press Enter to use config defaults.
    """
    log = get_logger()

    print()
    print("─" * 50)
    print("  Bing 搜索次数设置")
    print("─" * 50)

    pc_default = config.search.pc_count
    mobile_default = config.search.mobile_count

    try:
        pc_input = input(f"  PC 搜索次数 [默认 {pc_default}]: ").strip()
        pc_count = int(pc_input) if pc_input else pc_default

        mobile_input = input(f"  移动端搜索次数 [默认 {mobile_default}]: ").strip()
        mobile_count = int(mobile_input) if mobile_input else mobile_default
    except (KeyboardInterrupt, EOFError):
        log.info("Input cancelled, using config defaults")
        return pc_default, mobile_default
    except ValueError:
        log.warning("Invalid input, using config defaults")
        return pc_default, mobile_default

    print("─" * 50)
    print()
    return pc_count, mobile_count


def run_read_to_earn_only(config: Config) -> bool:
    """仅执行手机 Bing app '阅读以赚取'，跳过搜索和每日活动。"""
    log = get_logger()
    log.info("Read-Only 模式: 仅执行手机 Bing app '阅读以赚取'")

    if not config.mobile_app.enabled:
        log.error("config.yaml 中 mobile_app.enabled 未设为 true")
        return False

    emulator = AndroidEmulator(
        adb_path=config.mobile_app.adb_path,
        device_serial=config.mobile_app.device_serial,
        read_article_count=config.mobile_app.read_article_count,
        scroll_delay=config.mobile_app.scroll_delay,
        read_dwell_time=config.mobile_app.read_dwell_time,
        read_scrolls_per_article=config.mobile_app.read_scrolls_per_article,
    )
    return emulator.run_read_to_earn()


def main() -> None:
    """Main entry point."""
    print_banner()

    # 1. Load configuration
    config = load_config(Path("config.yaml"))

    # 2. Setup logging
    log = setup_logger(config.behavior.log_level)
    log.info("Starting Microsoft Rewards Auto-Farming")

    # 3. Prompt for search counts (override config)
    pc_count, mobile_count = prompt_search_counts(config)

    # 4. Load query banks
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
        if pc_count > 0:
            pc_queries = qg.generate_batch(
                pc_count, config.search.query_language
            )
            pc_done = search_handler.do_pc_searches(pc_queries)
            log.info(f"PC searches: {pc_done}/{pc_count} successful")
        else:
            pc_done = 0
            log.info("PC searches skipped (count=0)")

        # 8. Mobile searches
        if mobile_count > 0:
            mobile_queries = qg.generate_batch(
                mobile_count, config.search.query_language
            )
            mobile_done = search_handler.do_mobile_searches(mobile_queries)
            log.info(
                f"Mobile searches: {mobile_done}/{mobile_count} successful"
            )
        else:
            mobile_done = 0
            log.info("Mobile searches skipped (count=0)")

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

        # 10. Mobile app: Read to Earn (via ADB phone connection)
        read_earn_ok = False
        if "--no-read" in sys.argv:
            log.info("Mobile app 'Read to Earn' skipped (--no-read)")
        elif config.mobile_app.enabled:
            log.info("Starting Bing mobile app 'Read to Earn'...")
            emulator = AndroidEmulator(
                adb_path=config.mobile_app.adb_path,
                device_serial=config.mobile_app.device_serial,
                read_article_count=config.mobile_app.read_article_count,
                scroll_delay=config.mobile_app.scroll_delay,
                read_dwell_time=config.mobile_app.read_dwell_time,
                read_scrolls_per_article=config.mobile_app.read_scrolls_per_article,
            )
            read_earn_ok = emulator.run_read_to_earn()
            if read_earn_ok:
                log.info("Read to Earn completed")
            else:
                log.warning("Read to Earn encountered issues")
        else:
            log.info("Mobile app 'Read to Earn' disabled")

        # 11. Report final points
        dash.navigate()
        points_after = dash.get_points_info()
        earned = points_after.available - points_before.available
        task_summary = (
            f"PC searches={pc_done}/{pc_count}, "
            f"Mobile searches={mobile_done}/{mobile_count}, "
            f"Poll={'OK' if activity_results['poll'] else 'N/A'}, "
            f"Quizzes={activity_results['quizzes']}, "
            f"More={activity_results['more']}, "
            f"ReadToEarn={'OK' if read_earn_ok else 'N/A'}"
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
    if "--read-only" in sys.argv:
        config = load_config(Path("config.yaml"))
        setup_logger(config.behavior.log_level)
        ok = run_read_to_earn_only(config)
        sys.exit(0 if ok else 1)
    else:
        main()
