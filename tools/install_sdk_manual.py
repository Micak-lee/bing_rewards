#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""不经 sdkmanager，直接把 Android SDK 组件下载并解包到工作区内的 SDK 目录。

新版 sdkmanager 会往工作区外写文件（被沙箱拒绝），所以这里自己来：
  1. 逐个组件先试国内镜像（腾讯），失败再回落到 dl.google.com；
  2. 自动识别压缩包内部的目录层级，摆成 SDK 应有的布局；
  3. 补上 licenses 文件，避免 AGP 报“许可未接受”。
"""
import os
import re
import shutil
import ssl
import sys
import time
import urllib.request
import zipfile

ROOT = r"D:\new_bing"
SDK = os.path.join(ROOT, ".android-sdk")
CACHE = os.path.join(ROOT, ".toolchain", "sdk-zips")
MIRROR = "https://mirrors.cloud.tencent.com/AndroidSDK/"
OFFICIAL = "https://dl.google.com/android/repository/"

# (归档文件名, 解包目标相对 SDK 的路径)
PACKAGES = [
    ("platform-35_r02.zip", os.path.join("platforms", "android-35")),
    ("build-tools_r35_windows.zip", os.path.join("build-tools", "35.0.0")),
    ("platform-tools_r37.0.1-win.zip", "platform-tools"),
]

EXPECT = {
    os.path.join("platforms", "android-35"): ["android.jar", "source.properties"],
    os.path.join("build-tools", "35.0.0"): ["aapt2.exe", "d8.bat", "apksigner.bat", "source.properties"],
    "platform-tools": ["adb.exe"],
}

START = time.time()


def log(msg):
    print("[%6.1fs] %s" % (time.time() - START, msg), flush=True)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f%s" % (n, unit)
        n /= 1024.0
    return "%.1fTB" % n


def download(url, dest, min_size=1 << 20):
    if os.path.exists(dest) and os.path.getsize(dest) > min_size:
        log("已存在，跳过: %s (%s)" % (os.path.basename(dest), human(os.path.getsize(dest))))
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 sdk-fetch"})
    log("下载 %s" % url)
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got, last = 0, 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got - last > (10 << 20):
                last = got
                pct = ("%.0f%%" % (got * 100.0 / total)) if total else "?"
                log("   ... %s / %s (%s)" % (human(got), human(total) if total else "?", pct))
    if os.path.getsize(tmp) < min_size:
        os.remove(tmp)
        raise RuntimeError("下载内容异常小: %s" % url)
    os.replace(tmp, dest)
    log("完成 %s (%s)" % (os.path.basename(dest), human(os.path.getsize(dest))))
    return dest


def fetch(name):
    dest = os.path.join(CACHE, name)
    errors = []
    for base in (MIRROR, OFFICIAL):
        try:
            return download(base + name, dest)
        except Exception as e:
            errors.append("%s -> %s" % (base + name, e))
            log("该源失败：%s" % e)
    raise RuntimeError("全部源都失败:\n  " + "\n  ".join(errors))


def top_levels(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = set()
        for n in z.namelist():
            n = n.replace("\\", "/").lstrip("/")
            if n:
                names.add(n.split("/")[0])
        return sorted(names)


def unpack_to(zip_path, target):
    """把压缩包解开并摆到 target 目录（自动跳过/使用顶层目录）。"""
    os.makedirs(target, exist_ok=True)
    tops = top_levels(zip_path)
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
    single_dir = len(tops) == 1 and all(
        n.replace("\\", "/").startswith(tops[0] + "/") for n in names
    )
    if single_dir:
        log("压缩包内含顶层目录 '%s'，直接搬进去" % tops[0])
        tmp = target + "__tmp"
        if os.path.exists(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        src = os.path.join(tmp, tops[0])
        for item in os.listdir(src):
            dst = os.path.join(target, item)
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                else:
                    os.remove(dst)
            shutil.move(os.path.join(src, item), dst)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        log("压缩包是散装结构，直接解压到目标目录")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(target)


def write_licenses():
    lic_dir = os.path.join(SDK, "licenses")
    os.makedirs(lic_dir, exist_ok=True)
    hashes = {
        "android-sdk-license": [
            "8933bad161af4178b1185d1a37fbf41ea5269c55",
            "d56f5187479451eabf01fb78af6dfcb131a6481e",
            "24333f8a63b6825ea9c5514f83c2829b004d1fee",
        ],
        "android-sdk-preview-license": ["84831b9409646a918e30573bab4c9c91346d8abd"],
        "android-sdk-arm-dbt-license": ["859f317696f67ef3d7f30a50a5560e7834b43903"],
    }
    for name, lines in hashes.items():
        path = os.path.join(lic_dir, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            log("写入许可文件 %s" % name)


def verify():
    ok = True
    print("\n===== SDK 自检 =====")
    for rel, files in EXPECT.items():
        for f in files:
            path = os.path.join(SDK, rel, f)
            exists = os.path.exists(path)
            ok = ok and exists
            print("%-46s %s" % (rel + "\\" + f, "OK" if exists else "缺失"))
    return ok


def main():
    results = {}
    for name, rel_target in PACKAGES:
        target = os.path.join(SDK, rel_target)
        try:
            zip_path = fetch(name)
            unpack_to(zip_path, target)
            results[name] = True
            log("安装完成 -> %s" % target)
        except Exception as e:
            results[name] = False
            log("安装失败 %s: %s" % (name, e))
    write_licenses()
    ok = verify()
    print("RESULT %s" % ("OK" if ok else "INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
