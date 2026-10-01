#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在工作区内自举 Android 编译工具链（不需要管理员权限、不需要 Android Studio 图形界面）。

做三件事：
  1. 下载并解压 Gradle 发行版      -> D:\\new_bing\\.toolchain\\gradle-8.11.1
  2. 下载并解压 Android cmdline-tools -> D:\\new_bing\\.android-sdk\\cmdline-tools\\latest
  3. 用 sdkmanager 安装 platform-tools / platforms;android-35 / build-tools;35.0.0

所有产物都落在工作区内，避免沙箱对工作区外写入的限制。
"""
import os
import re
import ssl
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = r"D:\new_bing"
TC = os.path.join(ROOT, ".toolchain")
SDK = os.path.join(ROOT, ".android-sdk")
JBR = r"C:\Program Files\Android\Android Studio\jbr"
GRADLE_VERSION = "8.11.1"
REPO_URL = "https://dl.google.com/android/repository/repository2-3.xml"
GRADLE_URLS = [
    "https://services.gradle.org/distributions/gradle-%s-bin.zip" % GRADLE_VERSION,
    "https://mirrors.cloud.tencent.com/gradle/gradle-%s-bin.zip" % GRADLE_VERSION,
]
SDK_PACKAGES = ["platform-tools", "platforms;android-35", "build-tools;35.0.0"]

START = time.time()


def log(msg):
    print("[%6.1fs] %s" % (time.time() - START, msg), flush=True)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f%s" % (n, unit)
        n /= 1024.0
    return "%.1fTB" % n


def absolute_url(url):
    """Google 的清单里归档地址可能是相对路径，补齐主机名。"""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return "https://dl.google.com/android/repository/" + url.lstrip("/")


def download(url, dest, min_size=1024):
    """下载到 dest（带进度），已存在且大小合理则跳过。"""
    url = absolute_url(url)
    if os.path.exists(dest) and os.path.getsize(dest) > min_size:
        log("已存在，跳过下载: %s (%s)" % (dest, human(os.path.getsize(dest))))
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    log("下载 %s" % url)
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 toolchain-bootstrap"})
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            last = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if got - last > (8 << 20):
                    last = got
                    pct = ("%.1f%%" % (got * 100.0 / total)) if total else "?"
                    log("   ... %s / %s  (%s)" % (human(got), human(total) if total else "?", pct))
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError("下载失败 %s: %s" % (url, e))
    if os.path.getsize(tmp) < min_size:
        raise RuntimeError("下载内容过小，可能失败: %s" % tmp)
    os.replace(tmp, dest)
    log("完成 %s (%s)" % (dest, human(os.path.getsize(dest))))
    return dest


def unzip(zip_path, dest):
    os.makedirs(dest, exist_ok=True)
    log("解压 %s -> %s" % (os.path.basename(zip_path), dest))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest)
    return dest


def top_level_names(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = set()
        for n in z.namelist():
            n = n.replace("\\", "/").lstrip("/")
            if not n:
                continue
            names.add(n.split("/")[0])
        return sorted(names)


def fetch_text(url):
    log("抓取 %s" % url)
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 toolchain-bootstrap"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return r.read().decode("utf-8", "replace")


def find_archive_url(xml, pkg_path, host_os="windows"):
    """从 repository2-3.xml 里找出某个包的 Windows 归档地址。"""
    m = re.search(r'<remotePackage path="%s">(.*?)</remotePackage>' % re.escape(pkg_path), xml, re.S)
    if not m:
        return None
    block = m.group(1)
    windows, generic = None, None
    for a in re.findall(r"<archive>(.*?)</archive>", block, re.S):
        u = re.search(r"<url>(.*?)</url>", a)
        if not u:
            continue
        url = u.group(1).strip()
        ho = re.search(r'host-os="([^"]+)"', a)
        if ho and ho.group(1) == host_os:
            windows = url
        elif not ho:
            generic = url
    return windows or generic


def run(cmd, cwd=None, env=None, input_text=None, timeout=3600):
    log("执行: %s" % " ".join(cmd))
    p = subprocess.run(
        cmd, cwd=cwd, env=env, input=input_text, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    out = (p.stdout or "").strip()
    if out:
        tail = out.splitlines()
        for line in tail[-25:]:
            print("    | " + line, flush=True)
    log("退出码 %s" % p.returncode)
    return p.returncode, out


def step_gradle():
    marker = os.path.join(TC, "gradle-%s" % GRADLE_VERSION, "bin", "gradle.bat")
    if os.path.exists(marker):
        log("Gradle 已就绪: %s" % marker)
        return marker
    zip_path = os.path.join(TC, "gradle-%s-bin.zip" % GRADLE_VERSION)
    last_err = None
    for url in GRADLE_URLS:
        try:
            download(url, zip_path, min_size=50 << 20)
            last_err = None
            break
        except Exception as e:
            last_err = e
            log("该源失败，尝试下一个: %s" % e)
    if last_err:
        raise last_err
    unzip(zip_path, TC)
    if not os.path.exists(marker):
        raise RuntimeError("解压后找不到 gradle.bat: %s" % marker)
    log("Gradle 就绪: %s" % marker)
    return marker


def step_cmdline_tools():
    marker = os.path.join(SDK, "cmdline-tools", "latest", "bin", "sdkmanager.bat")
    if os.path.exists(marker):
        log("cmdline-tools 已就绪: %s" % marker)
        return marker
    xml = fetch_text(REPO_URL)
    url = find_archive_url(xml, "cmdline-tools;latest") or \
        "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    zip_path = os.path.join(TC, "cmdline-tools.zip")
    download(url, zip_path, min_size=10 << 20)
    tmp = os.path.join(TC, "cmdline-tools-extract")
    if os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    unzip(zip_path, tmp)
    # 归档内是 cmdline-tools/<bin,lib,...>，需要落到 cmdline-tools/latest/
    src = os.path.join(tmp, "cmdline-tools")
    dst = os.path.join(SDK, "cmdline-tools", "latest")
    if os.path.exists(dst):
        shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        shutil.move(src, dst)
    else:
        shutil.move(tmp, dst)
    shutil.rmtree(tmp, ignore_errors=True)
    if not os.path.exists(marker):
        raise RuntimeError("cmdline-tools 布局异常，找不到 %s" % marker)
    log("cmdline-tools 就绪")
    return marker


def step_sdk_packages(sdkmanager):
    java_home = JBR if os.path.isdir(JBR) else os.environ.get("JAVA_HOME", "")
    env = dict(os.environ)
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")
    log("JAVA_HOME=%s" % env.get("JAVA_HOME"))

    # 先接受许可（sdkmanager 会连续提问，喂 y）
    run([sdkmanager, "--sdk_root=%s" % SDK, "--licenses"], env=env, input_text="y\n" * 40)

    missing = []
    if not os.path.exists(os.path.join(SDK, "platforms", "android-35", "android.jar")):
        missing.append("platforms;android-35")
    if not os.path.exists(os.path.join(SDK, "build-tools", "35.0.0", "aapt2.exe")):
        missing.append("build-tools;35.0.0")
    if not os.path.exists(os.path.join(SDK, "platform-tools", "adb.exe")):
        missing.append("platform-tools")
    if not missing:
        log("SDK 组件已齐全")
        return
    code, out = run([sdkmanager, "--sdk_root=%s" % SDK, "--install"] + missing, env=env, input_text="y\n" * 40)
    if code != 0:
        log("sdkmanager 安装返回非零，稍后校验实际产物")


def verify():
    checks = {
        "gradle.bat": os.path.join(TC, "gradle-%s" % GRADLE_VERSION, "bin", "gradle.bat"),
        "sdkmanager.bat": os.path.join(SDK, "cmdline-tools", "latest", "bin", "sdkmanager.bat"),
        "android.jar(35)": os.path.join(SDK, "platforms", "android-35", "android.jar"),
        "aapt2.exe(35)": os.path.join(SDK, "build-tools", "35.0.0", "aapt2.exe"),
        "d8.bat(35)": os.path.join(SDK, "build-tools", "35.0.0", "d8.bat"),
        "apksigner.bat": os.path.join(SDK, "build-tools", "35.0.0", "apksigner.bat"),
    }
    print("\n===== 工具链自检 =====")
    ok = True
    for name, path in checks.items():
        exists = os.path.exists(path)
        ok = ok and exists
        print("%-16s %s  %s" % (name, "OK  " if exists else "缺失", path))
    try:
        total, used, free = shutil.disk_usage(ROOT)
        print("D 盘剩余空间: %.1f GB" % (free / (1 << 30)))
    except Exception:
        pass
    print("工具链状态: %s" % ("全部就绪" if ok else "仍有缺失"))
    return ok


def main():
    os.makedirs(TC, exist_ok=True)
    os.makedirs(SDK, exist_ok=True)
    steps = [("gradle", step_gradle), ("cmdline-tools", step_cmdline_tools)]
    results = {}
    for name, fn in steps:
        try:
            results[name] = fn()
        except Exception as e:
            log("步骤 %s 失败: %s" % (name, e))
            results[name] = None
    if results.get("cmdline-tools"):
        try:
            step_sdk_packages(results["cmdline-tools"])
        except Exception as e:
            log("安装 SDK 组件失败: %s" % e)
    ok = verify()
    print("RESULT %s" % ("OK" if ok else "INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
