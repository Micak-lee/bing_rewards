#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用已保存的登录态打开微软奖励面板，打印积分与「阅读以赚取」进度。

只读，不做任何点击；用于核对手机端自动阅读是否真的加了积分。
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "auth_state.json")
URL = "https://rewards.bing.com/"

ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--mute-audio",
]


def main():
    if not os.path.exists(STATE):
        print("找不到登录态文件: %s" % STATE)
        return 2
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=ARGS)
        ctx = browser.new_context(storage_state=STATE, locale="zh-CN")
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)
        print("URL  :", page.url)
        print("TITLE:", page.title())
        try:
            text = page.inner_text("body")
        except Exception as e:
            print("读取正文失败:", e)
            browser.close()
            return 3
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        print("---- 正文前 80 行 ----")
        for ln in lines[:80]:
            print("   ", ln)
        print("---- 关键行 ----")
        for ln in lines:
            if re.search(r"积分|points|阅读|Read|赚取|每日活动|搜索", ln, re.I):
                print("   *", ln)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
