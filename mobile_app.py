"""Bing mobile app automation via ADB (Android real phone).

Handles "阅读以赚取" (Read to Earn) points inside the Bing app's Rewards page.

Two connection methods:
  1. USB ADB: Connect phone via USB, enable USB debugging → `adb devices` detects it
  2. Phone Link (连接至Windows): Phone is linked via Microsoft Phone Link,
     then connect ADB over WiFi for automation.

Requirements:
  - Android phone with USB debugging enabled
  - ADB (Android Debug Bridge) in PATH or configured path
  - Bing app installed on phone and logged into Microsoft account
"""
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from logger import get_logger

BING_PACKAGE = "com.microsoft.bing"
BING_LAUNCH_ACTIVITY = "com.microsoft.bing.client.MainActivity"

# Deeplink: try to open Rewards page directly
# Some Bing app versions support this URI scheme
BING_REWARDS_DEEPLINK = "microsoft.bing://rewards"
BING_REWARDS_ACTIVITY = "com.microsoft.bing.client.rewards.RewardsActivity"


@dataclass
class UIElement:
    """Represents a UI element found via uiautomator dump."""
    text: str = ""
    content_desc: str = ""
    bounds: str = ""
    clickable: bool = False
    resource_id: str = ""
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0

    @property
    def center_x(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def center_y(self) -> int:
        return (self.y1 + self.y2) // 2


class AndroidEmulator:
    """Interact with Android emulator/device via ADB for Bing app automation."""

    def __init__(self, adb_path: str = "adb", device_serial: str = "",
                 read_article_count: int = 30, scroll_delay: float = 3.0,
                 read_dwell_time: float = 10.0, read_scrolls_per_article: int = 3):
        self._adb = adb_path
        self._serial = device_serial
        self._read_count = read_article_count
        self._scroll_delay = scroll_delay
        self._dwell_time = read_dwell_time
        self._scrolls_per_article = read_scrolls_per_article
        self._log = get_logger()
        self._screen_width = 1080
        self._screen_height = 1920

    def _adb_cmd(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run an ADB command and return the result."""
        cmd = [self._adb]
        if self._serial:
            cmd += ["-s", self._serial]
        cmd += args
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

    def _get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions via ADB."""
        try:
            result = self._adb_cmd(["shell", "wm", "size"])
            match = re.search(r"(\d+)x(\d+)", result.stdout)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                self._screen_width, self._screen_height = w, h
                return w, h
        except Exception:
            pass
        return self._screen_width, self._screen_height

    # ── Public API ──────────────────────────────────────────────

    def check_connection(self) -> bool:
        """Check if any Android device is connected via ADB (USB or WiFi)."""
        result = self._adb_cmd(["devices"])
        lines = result.stdout.strip().split("\n")[1:]
        for line in lines:
            if line.strip() and "device" in line and "offline" not in line:
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[1] == "device":
                    device_id = parts[0]
                    self._log.info(f"Phone connected: {device_id}")
                    self._get_screen_size()
                    return True
        return False

    def is_bing_installed(self) -> bool:
        """Check if Bing app is installed."""
        result = self._adb_cmd(["shell", "pm", "list", "packages", BING_PACKAGE])
        return BING_PACKAGE in result.stdout

    def _resolve_launcher_activity(self) -> Optional[str]:
        """Resolve the Bing app's launcher activity via package manager.

        Returns activity name like 'com.microsoft.bing.client.MainActivity',
        or None if unable to resolve.
        """
        try:
            result = self._adb_cmd([
                "shell", "cmd", "package", "resolve-activity",
                "--brief", BING_PACKAGE,
            ])
            lines = result.stdout.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("/"):
                    activity = line.lstrip("/").strip()
                    if activity:
                        self._log.debug(f"Resolved launcher: {activity}")
                        return activity
        except Exception:
            pass

        # Fallback: parse pm dump
        try:
            result = self._adb_cmd([
                "shell", "dumpsys", "package", BING_PACKAGE,
            ])
            # Look for the MAIN intent filter's activity
            in_main = False
            for line in result.stdout.split("\n"):
                if "Main" in line and "ACTIVITY" in line:
                    in_main = True
                    continue
                if in_main and line.strip().startswith("  "):
                    # Activity name is often after a slash: com.microsoft.bing/.client.MainActivity
                    continue
                if in_main and "ActivityResolver" in line:
                    continue
        except Exception:
            pass

        return None

    def launch_bing(self) -> bool:
        """Launch Bing app on the device.

        Tries multiple methods to find the correct launch activity.
        """
        # Strategy 1: resolve launcher activity dynamically, then launch
        resolved = self._resolve_launcher_activity()
        if resolved:
            try:
                result = self._adb_cmd([
                    "shell", "am", "start",
                    "-n", f"{BING_PACKAGE}/{resolved}",
                ])
                if result.returncode == 0 and "Error" not in result.stdout:
                    self._log.info(f"Bing app launched (resolved: {resolved})")
                    time.sleep(4)
                    return True
            except Exception:
                pass

        # Strategy 2: monkey tool (auto-detects launcher activity)
        try:
            result = self._adb_cmd(["shell", "monkey", "-p", BING_PACKAGE, "1"])
            if result.returncode == 0 and "Error" not in result.stderr:
                self._log.info("Bing app launched (monkey)")
                time.sleep(4)
                return True
        except Exception:
            pass

        # Strategy 3: direct activity launch with known name
        try:
            result = self._adb_cmd([
                "shell", "am", "start",
                "-n", f"{BING_PACKAGE}/{BING_LAUNCH_ACTIVITY}",
            ])
            if result.returncode == 0 and "Error" not in result.stdout:
                self._log.info("Bing app launched (direct activity)")
                time.sleep(4)
                return True
            self._log.debug(f"am start output: {result.stdout[:200]}")
        except Exception as e:
            self._log.warning(f"am start failed: {e}")

        # Strategy 4: package-based launch (resolves main activity automatically)
        try:
            result = self._adb_cmd([
                "shell", "am", "start",
                "-p", BING_PACKAGE,
            ])
            if result.returncode == 0 and "Error" not in result.stdout:
                self._log.info("Bing app launched (package-based)")
                time.sleep(4)
                return True
        except Exception:
            pass

        return False

    def go_back(self) -> None:
        """Press Android back button."""
        self._adb_cmd(["shell", "input", "keyevent", "KEYCODE_BACK"])
        time.sleep(1)

    def force_stop_bing(self) -> None:
        """Force-stop the Bing app."""
        self._adb_cmd(["shell", "am", "force-stop", BING_PACKAGE])
        self._log.info("Bing app force-stopped")

    # ── UI Interaction ──────────────────────────────────────────

    def dump_ui(self) -> Optional[str]:
        """Dump current screen UI XML via uiautomator and return as string."""
        try:
            self._adb_cmd(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
            tmpdir = tempfile.gettempdir()
            local_path = Path(tmpdir) / "msrewards_ui.xml"
            self._adb_cmd(["pull", "/sdcard/ui.xml", str(local_path)])
            if not local_path.exists():
                return None
            text = local_path.read_bytes().decode("utf-8", errors="replace")
            return text
        except Exception as e:
            self._log.debug(f"UI dump failed: {e}")
            return None

    def find_elements_by_text(self, text: str, partial: bool = True,
                              clickable_only: bool = False) -> list[UIElement]:
        """Find UI elements whose text/content-desc matches the given string."""
        xml_str = self.dump_ui()
        if not xml_str:
            return []

        elements = []
        try:
            root = ET.fromstring(xml_str)
            self._parse_node(root, text, partial, elements)
        except ET.ParseError:
            pass

        if clickable_only:
            elements = [e for e in elements if e.clickable]

        return elements

    def find_elements_by_resource_id(self, resource_id: str) -> list[UIElement]:
        """Find UI elements by resource-id."""
        xml_str = self.dump_ui()
        if not xml_str:
            return []
        elements = []
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                rid = (node.get("resource-id", "") or "").strip()
                if rid and rid.endswith(resource_id):
                    bounds = node.get("bounds", "")
                    if bounds:
                        x1, y1, x2, y2 = self._parse_bounds(bounds)
                        elements.append(UIElement(
                            text=(node.get("text", "") or "").strip(),
                            content_desc=(node.get("content-desc", "") or "").strip(),
                            bounds=bounds,
                            clickable=node.get("clickable", "false") == "true",
                            resource_id=rid,
                            x1=x1, y1=y1, x2=x2, y2=y2,
                        ))
        except ET.ParseError:
            pass
        return elements

    def _parse_node(self, node: ET.Element, text: str,
                    partial: bool, results: list):
        node_text = (node.get("text", "") or "").strip()
        node_desc = (node.get("content-desc", "") or "").strip()
        bounds = node.get("bounds", "")
        clickable = node.get("clickable", "false") == "true"
        rid = (node.get("resource-id", "") or "").strip()

        if partial:
            match = text in node_text or text in node_desc
        else:
            match = node_text == text or node_desc == text

        if match and bounds:
            x1, y1, x2, y2 = self._parse_bounds(bounds)
            results.append(UIElement(
                text=node_text, content_desc=node_desc,
                bounds=bounds, clickable=clickable, resource_id=rid,
                x1=x1, y1=y1, x2=x2, y2=y2,
            ))

        for child in node:
            self._parse_node(child, text, partial, results)

    def _parse_bounds(self, bounds: str) -> tuple:
        nums = re.findall(r"\d+", bounds)
        if len(nums) >= 4:
            return int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3])
        return 0, 0, 0, 0

    def tap(self, x: int, y: int) -> bool:
        """Tap at screen coordinates (x, y)."""
        try:
            self._adb_cmd(["shell", "input", "tap", str(x), str(y)])
            return True
        except Exception:
            return False

    def tap_element(self, element: UIElement) -> bool:
        """Tap the center of a UI element."""
        self._log.debug(f"Tapping '{element.text or element.content_desc}' "
                        f"at ({element.center_x}, {element.center_y})")
        time.sleep(0.5)
        return self.tap(element.center_x, element.center_y)

    def click_text(self, text: str, partial: bool = True) -> bool:
        """Click the first matching element containing the given text."""
        elements = self.find_elements_by_text(text, partial, clickable_only=True)
        if not elements:
            elements = self.find_elements_by_text(text, partial)
        if not elements:
            self._log.debug(f"No element found with text: '{text}'")
            return False
        return self.tap_element(elements[0])

    def scroll_down(self) -> bool:
        """Perform a swipe gesture to scroll down."""
        try:
            w, h = self._screen_width, self._screen_height
            sx, sy = w // 2, h * 3 // 4
            ex, ey = w // 2, h // 4
            self._adb_cmd([
                "shell", "input", "swipe",
                str(sx), str(sy), str(ex), str(ey), "600",
            ])
            return True
        except Exception as e:
            self._log.debug(f"Scroll failed: {e}")
            return False

    def wait_for_text(self, text: str, timeout: int = 10,
                      partial: bool = True) -> bool:
        """Wait for text to appear on screen, polling once per second."""
        for _ in range(timeout):
            if self.find_elements_by_text(text, partial):
                return True
            time.sleep(1)
        return False

    def take_screenshot(self, name: str = "debug") -> None:
        """Save a screenshot from the device for debugging."""
        try:
            tmpdir = tempfile.gettempdir()
            local_path = Path(tmpdir) / f"msrewards_{name}.png"
            self._adb_cmd(["shell", "screencap", "/sdcard/msrewards_debug.png"])
            self._adb_cmd(["pull", "/sdcard/msrewards_debug.png", str(local_path)])
            self._log.info(f"Screenshot saved: {local_path}")
        except Exception as e:
            self._log.debug(f"Screenshot failed: {e}")

    # ── Navigation Flow ─────────────────────────────────────────

    def _is_rewards_page(self) -> bool:
        """Check if current screen looks like a Rewards page.

        Looks for keywords that appear on the Rewards page.
        """
        # Quick check for common Rewards page content
        for keyword in ["阅读以赚取", "Read to Earn", "奖励积分", "每日签到"]:
            if self.find_elements_by_text(keyword, partial=True):
                return True
        # Check for points display (common pattern like "12,345")
        for elem in self.find_elements_by_text(",", partial=True):
            text = elem.text or ""
            if any(c.isdigit() for c in text) and len(text) > 3:
                # Found a number, could be points — likely on Rewards page
                return True
        return False

    def _find_bottom_nav_items(self) -> list[UIElement]:
        """Find clickable items in the bottom navigation bar area.

        Uses uiautomator dump to find elements near the bottom of the screen
        that are likely nav bar tabs.
        """
        xml_str = self.dump_ui()
        if not xml_str:
            return []
        items = []
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                clickable = node.get("clickable", "false") == "true"
                bounds = node.get("bounds", "")
                if not clickable or not bounds:
                    continue
                x1, y1, x2, y2 = self._parse_bounds(bounds)
                # Bottom nav items: in the bottom 15% of screen, reasonably wide
                if y1 > self._screen_height * 0.80 and (x2 - x1) > 50:
                    items.append(UIElement(
                        text=(node.get("text", "") or "").strip(),
                        content_desc=(node.get("content-desc", "") or "").strip(),
                        bounds=bounds, clickable=True,
                        x1=x1, y1=y1, x2=x2, y2=y2,
                    ))
        except ET.ParseError:
            pass
        # Sort left to right
        items.sort(key=lambda e: e.x1)
        return items

    def _navigate_to_rewards_tab(self) -> bool:
        """Navigate from Bing main screen to the Rewards tab.

        The Bing Android app has a bottom navigation bar with tabs like
        '首页'(Home), '奖励'(Rewards), etc. We need to find and tap the Rewards tab.

        Multiple strategies with fallback:
          1. Try deeplink to rewards activity directly
          2. Try direct rewards activity
          3. Scan bottom nav items and try each one
          4. Try text-based search in bottom area
          5. Manual instruction for user
        """
        # Strategy 1: Deeplink
        try:
            self._log.info("Trying deeplink to Rewards page...")
            self._adb_cmd([
                "shell", "am", "start",
                "-d", BING_REWARDS_DEEPLINK,
            ])
            time.sleep(3)
            if self._is_rewards_page():
                self._log.info("Deeplink navigated to Rewards page")
                return True
        except Exception:
            pass

        # Strategy 2: Direct rewards activity
        try:
            self._log.info("Trying direct Rewards activity...")
            self._adb_cmd([
                "shell", "am", "start",
                "-n", f"{BING_PACKAGE}/{BING_REWARDS_ACTIVITY}",
            ])
            time.sleep(3)
            if self._is_rewards_page():
                self._log.info("Direct activity navigated to Rewards page")
                return True
        except Exception:
            pass

        # Strategy 3: Scan bottom nav items
        self._log.info("Scanning bottom navigation bar...")
        nav_items = self._find_bottom_nav_items()
        self._log.info(f"Found {len(nav_items)} bottom nav items")

        for idx, item in enumerate(nav_items):
            label = item.text or item.content_desc or f"item{idx}"
            self._log.debug(f"  [{idx}] ({item.center_x}, {item.center_y}) '{label}'")
            self.tap_element(item)
            time.sleep(3)
            if self._is_rewards_page():
                self._log.info(f"Rewards tab found at position {idx}")
                return True
            # If we see reading-related content, even better
            if self.find_elements_by_text("阅读", partial=True):
                self._log.info("Found reading content after tapping nav item")
                return True
            self.go_back()
            time.sleep(1)

        # Strategy 4: Try "更多" / "More" button to reveal hidden tabs
        self._log.info("Looking for '更多' / 'More' button...")
        for more_text in ["更多", "More", "more"]:
            more_btns = self.find_elements_by_text(more_text, partial=False)
            more_btns = [e for e in more_btns if e.y1 > self._screen_height * 0.75]
            if more_btns:
                self.tap_element(more_btns[0])
                time.sleep(3)
                # Now scan nav items again
                for item in self._find_bottom_nav_items():
                    self.tap_element(item)
                    time.sleep(2)
                    if self._is_rewards_page():
                        return True
                    self.go_back()
                    time.sleep(1)
                break

        self._log.warning("Could not find Rewards tab")

        # Final fallback: ask user
        self._log.info("=" * 50)
        self._log.info("请在手机上手动打开 Bing app 的 Rewards 页面")
        self._log.info("然后按 ENTER 继续...")
        self._log.info("=" * 50)
        try:
            input(">>> Press ENTER after navigating to Rewards: ")
            if self._is_rewards_page():
                return True
        except (KeyboardInterrupt, EOFError):
            pass

        return False

    def _find_and_start_read_to_earn(self) -> bool:
        """Find and click the '阅读以赚取' card inside the Rewards page.

        The Rewards page shows activity cards including:
        - "阅读以赚取" / "Read to Earn"
        - Daily poll, quiz, etc.

        Returns True if we successfully entered the reading activity.
        """
        self._log.info("Looking for '阅读以赚取' in Rewards page...")

        # Try exact match first, then partial
        read_labels = [
            "阅读以赚取", "Read to Earn", "阅读赚取",
            "阅读", "read to earn", "Read to earn",
        ]

        for label in read_labels:
            if self.click_text(label, partial=False):
                self._log.info(f"Clicked '{label}'")
                time.sleep(3)
                return True

        for label in read_labels:
            if self.click_text(label, partial=True):
                self._log.info(f"Clicked '{label}' (partial match)")
                time.sleep(3)
                return True

        # If not visible, try scrolling down the Rewards page to reveal more cards
        self._log.info("Scrolling Rewards page to find more activities...")
        for _ in range(5):
            self.scroll_down()
            time.sleep(1.5)
            for label in ["阅读以赚取", "Read to Earn", "阅读"]:
                if self.click_text(label, partial=True):
                    time.sleep(3)
                    return True

        return False

    def _dump_ui_text(self) -> None:
        """Log all text on the current screen for debugging."""
        xml_str = self.dump_ui()
        if not xml_str:
            return
        texts = set()
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                t = (node.get("text", "") or "").strip()
                if t:
                    texts.add(t)
                cd = (node.get("content-desc", "") or "").strip()
                if cd:
                    texts.add(f"[desc]{cd}")
        except ET.ParseError:
            pass
        if texts:
            self._log.info("--- Page content ---")
            for t in sorted(texts):
                self._log.info(f"  {t[:100]}")

    def _find_headlines(self) -> list[UIElement]:
        """Find clickable elements that look like article headlines.

        Scans UI for elements with:
        - clickable=true
        - Position NOT in bottom nav area
        - Text length > 8 characters (headline-like)
        OR bounds large enough to be an article card.
        """
        xml_str = self.dump_ui()
        if not xml_str:
            return []
        candidates = []
        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                clickable = node.get("clickable", "false") == "true"
                bounds = node.get("bounds", "")
                if not clickable or not bounds:
                    continue
                text = (node.get("text", "") or "").strip()
                cd = (node.get("content-desc", "") or "").strip()
                x1, y1, x2, y2 = self._parse_bounds(bounds)
                w, h = x2 - x1, y2 - y1
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Skip bottom nav area
                if cy > self._screen_height * 0.80:
                    continue
                # Skip very small elements (icons, buttons under 60px)
                if w < 60 and h < 60:
                    continue

                score = 0
                # Bonus for having headline-length text
                if len(text) > 8:
                    score += 10
                elif len(cd) > 8:
                    score += 8
                # Bonus for wide elements (card-like)
                if w > self._screen_width * 0.5:
                    score += 5
                # Penalty for very tall elements (likely containers)
                if h > self._screen_height * 0.5:
                    score -= 20
                # Bonus for upper-mid screen (first few articles)
                if cy < self._screen_height * 0.5:
                    score += 3

                candidates.append((score, cx, cy, text or cd[:30]))

        except ET.ParseError:
            pass

        candidates.sort(key=lambda c: (c[0], c[2]), reverse=True)
        return candidates

    def _tap_first_article_card(self) -> bool:
        """Click on an article to open it.

        Multiple strategies:
          1. Find headline-like clickable elements by text/bounds scoring
          2. Tap center of the first visible content area
        """
        # Strategy 1: Score-based headline detection
        headlines = self._find_headlines()
        if headlines:
            score, cx, cy, label = headlines[0]
            self._log.debug(f"Tapping article '{label}' at ({cx}, {cy}) [score={score}]")
            return self.tap(cx, cy)

        # Strategy 2: Tap upper-center of screen (where first article usually is)
        w, h = self._screen_width, self._screen_height
        tap_x = w // 2
        tap_y = int(h * 0.30)  # ~30% from top, where first article typically appears
        self._log.debug(f"Tapping screen center at ({tap_x}, {tap_y})")
        return self.tap(tap_x, tap_y)

    def _scroll_inside_article(self) -> None:
        """Scroll up and down inside an open article to simulate reading."""
        for _ in range(self._scrolls_per_article):
            # Scroll down
            self.scroll_down()
            time.sleep(self._scroll_delay)
            # Scroll up a bit (shorter swipe)
            try:
                w, h = self._screen_width, self._screen_height
                start_x, start_y = w // 2, h // 3
                end_x, end_y = w // 2, h * 2 // 3
                self._adb_cmd([
                    "shell", "input", "swipe",
                    str(start_x), str(start_y),
                    str(end_x), str(end_y), "500",
                ])
                time.sleep(self._scroll_delay)
            except Exception:
                pass

    def _read_articles_inner(self) -> int:
        """Read articles by entering each one, scrolling inside, and dwelling.

        For each article:
          1. Click an article card in the list to open it
          2. Scroll up/down inside the article (~10 seconds)
          3. Go back to the article list
          4. Scroll the list to reveal the next article

        Returns the number of articles read.
        """
        self._log.info(f"Reading {self._read_count} articles "
                       f"(dwell={self._dwell_time}s, "
                       f"{self._scrolls_per_article} scrolls inside each)...")

        time.sleep(3)  # wait for feed to load
        self._dump_ui_text()  # debug: log page content

        read_count = 0
        for i in range(self._read_count):
            # 1. Click on an article to open it
            if not self._tap_first_article_card():
                # If tap fails, scroll down and try again
                self.scroll_down()
                time.sleep(2)
                if not self._tap_first_article_card():
                    self._log.debug(f"Could not tap article {i + 1}, skipping")
                    self.scroll_down()
                    time.sleep(self._scroll_delay)
                    continue

            time.sleep(2)  # wait for article to load

            # 2. Scroll inside the article
            self._scroll_inside_article()

            # 3. Dwell (the article is already open, stay to simulate reading)
            remaining = self._dwell_time - (
                self._scrolls_per_article * self._scroll_delay * 2
            )
            if remaining > 0:
                self._log.debug(f"Dwelling for {remaining:.0f}s...")
                time.sleep(remaining)

            # 4. Go back to article list
            self.go_back()
            time.sleep(2)

            read_count += 1
            if (i + 1) % 5 == 0:
                self._log.info(f"Read progress: {i + 1}/{self._read_count}")

            # Scroll the feed to expose next article
            self.scroll_down()
            time.sleep(self._scroll_delay)

        return read_count

    # ── Main Flow ───────────────────────────────────────────────

    def run_read_to_earn(self) -> bool:
        """Read Bing home page articles to earn points (3 pts/article, max 30).

        Flow: launch Bing app → home page news feed → read 10 articles.
        No Rewards tab navigation needed — the home page articles themselves
        are the "阅读以赚取" activity.

        Returns True if flow completed without critical error.
        """
        if not self.check_connection():
            self._log.error("No Android device detected.")
            return False

        if not self.is_bing_installed():
            self._log.error("Bing app is not installed. "
                           f"Please install '{BING_PACKAGE}' first.")
            return False

        if not self.launch_bing():
            self._log.error("Failed to launch Bing app.")
            self.take_screenshot("launch_failed")
            return False

        # Read articles directly from the home page news feed
        read_count = self._read_articles_inner()
        self._log.info(f"Read to earn completed: {read_count} articles read")
        return True
