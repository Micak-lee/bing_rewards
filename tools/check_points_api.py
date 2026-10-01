#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 auth_state.json 里的 Cookie 直接请求微软奖励接口，读出积分与各任务进度。

不启动浏览器、不用子进程管道，因此在沙箱里也能跑。
"""
import json
import os
import re
import ssl
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "auth_state.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0")

API_URLS = [
    "https://rewards.bing.com/api/getuserinfo?type=1&X-Requested-With=XMLHttpRequest",
    "https://rewards.bing.com/api/getuserinfo?X-Requested-With=XMLHttpRequest",
    "https://rewards.bing.com/",
]


def load_cookies():
    with open(STATE, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies") or []
    by_domain = {}
    for c in cookies:
        dom = (c.get("domain") or "").lstrip(".")
        by_domain.setdefault(dom, []).append(c)
    return by_domain


def cookie_header(by_domain, host):
    parts = []
    for dom, items in by_domain.items():
        if host.endswith(dom) or dom.endswith(host):
            for c in items:
                parts.append("%s=%s" % (c["name"], c["value"]))
    return "; ".join(parts)


def fetch(url, cookie):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://rewards.bing.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie,
    })
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        raw = r.read()
        return r.status, r.headers.get("Content-Type", ""), raw


def main():
    if not os.path.exists(STATE):
        print("找不到 %s" % STATE)
        return 2
    by_domain = load_cookies()
    print("登录态里的域:", ", ".join(sorted(by_domain.keys())))
    host = "rewards.bing.com"
    cookie = cookie_header(by_domain, host)
    print("匹配到的 Cookie 数量:", len(cookie.split("; ")) if cookie else 0)
    for url in API_URLS:
        try:
            status, ctype, raw = fetch(url, cookie)
        except Exception as e:
            print("请求失败 %s -> %s" % (url, e))
            continue
        print("\n==== %s -> %s (%s, %d 字节) ====" % (url, status, ctype, len(raw)))
        text = raw.decode("utf-8", "replace")
        if "json" in ctype or text.lstrip().startswith("{"):
            try:
                data = json.loads(text)
                summary(data)
            except Exception as e:
                print("JSON 解析失败:", e)
                print(text[:1500])
        else:
            print("(非 JSON 响应，长度 %d)" % len(text))
            m = re.findall(r"[\d,]{3,}\s*(?:积分|points)", text, re.I)
            if m:
                print("页面里出现的积分数:", m[:10])
        break
    return 0


def summary(data, prefix=""):
    """挑出跟积分/阅读有关的字段打印出来。"""
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, path + "/" + str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:6]):
                walk(v, path + "[%d]" % i)
        else:
            low = path.lower()
            if any(w in low for w in ("point", "balance", "read", "earn", "count", "progress", "credit")):
                if isinstance(obj, (int, float, str)) and str(obj).strip() != "":
                    print("  %-70s = %s" % (path, str(obj)[:80]))
    walk(data)
    print("---- 顶层键 ----")
    if isinstance(data, dict):
        print("  " + ", ".join(list(data.keys())[:25]))


if __name__ == "__main__":
    sys.exit(main())
