"""
Android 手机 ADB 连接助手

检查并帮助设置手机与电脑的 ADB 连接，用于 Bing app 自动化。
支持 USB 连接和 WiFi 连接两种方式。
"""
import subprocess
import sys
from pathlib import Path

ADB_PATH = "adb"


def run_adb(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [ADB_PATH] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)


def check_adb_exists() -> bool:
    try:
        result = run_adb(["version"])
        if result.returncode == 0:
            print(f"ADB 版本: {result.stdout.splitlines()[0]}")
            return True
    except FileNotFoundError:
        pass
    return False


def list_devices() -> list[str]:
    result = run_adb(["devices"])
    lines = result.stdout.strip().split("\n")[1:]
    devices = []
    for line in lines:
        if line.strip() and "device" in line and "offline" not in line:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
    return devices


def print_wifi_guide():
    print()
    print("=" * 60)
    print("WiFi ADB 连接指南（不需要 USB 线）")
    print("=" * 60)
    print()
    print("前提条件: 手机已通过 Phone Link (连接至 Windows) 与电脑配对")
    print()
    print("方法 1: 通过 Phone Link + WiFi ADB")
    print("  (1) 手机开启开发者选项和 USB 调试")
    print("  (2) 手机和电脑连接同一 WiFi")
    print("  (3) 运行: adb connect <手机IP地址>:5555")
    print()
    print("方法 2: 先 USB 连接一次，切换到 WiFi 模式")
    print("  (1) USB 连接手机到电脑")
    print("  (2) 运行: adb tcpip 5555")
    print("  (3) 拔掉 USB，运行: adb connect <手机IP>:5555")
    print()
    print("查看手机 IP 地址: 设置 → 关于手机 → 状态信息 → IP地址")
    print("=" * 60)


def print_usb_guide():
    print()
    print("=" * 60)
    print("USB 连接指南")
    print("=" * 60)
    print()
    print("  (1) 手机开启「开发者选项」:")
    print("       设置 → 关于手机 → 连续点击「版本号」7 次")
    print("  (2) 开启「USB 调试」:")
    print("       设置 → 系统 → 开发者选项 → USB 调试 → 开启")
    print("  (3) 用 USB 线连接电脑")
    print("  (4) 手机上弹窗确认「允许 USB 调试?」→ 勾选「一律允许」→ 确定")
    print("  (5) 重新运行本脚本检查")
    print("=" * 60)


def main():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   手机 ADB 连接助手 - Bing Rewards       ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # Step 1: Check ADB
    print("[1] 检查 ADB...")
    if not check_adb_exists():
        print("  ✗ ADB 未找到！请安装 Android SDK Platform Tools:")
        print("    https://developer.android.com/tools/releases/platform-tools")
        print("    下载后把 adb.exe 所在目录加入系统 PATH")
        sys.exit(1)
    print("  ✓ ADB 正常工作")
    print()

    # Step 2: Check devices
    print("[2] 检查连接的手机...")
    devices = list_devices()
    if devices:
        print(f"  ✓ 已连接 {len(devices)} 台设备:")
        for i, dev in enumerate(devices, 1):
            print(f"    {i}. {dev}")

        print()
        print("  在 config.yaml 中设置:")
        print(f'    device_serial: "{devices[0]}"')
        print("  或留空自动选择第一台设备")
        print()
        print("  Bing app 包名: com.microsoft.bing")
        result = run_adb(["shell", "pm", "list", "packages", "com.microsoft.bing"])
        if "com.microsoft.bing" in result.stdout:
            print("  ✓ Bing app 已安装")
        else:
            print("  ✗ Bing app 未安装，请通过 Play 商店或 APKPure 安装")
    else:
        print("  ✗ 未检测到手机")
        print()
        print("请选择连接方式:")
        print("  1. USB 连接")
        print("  2. WiFi 连接（适合 Phone Link 用户）")
        print()
        choice = input("请输入 1 或 2: ").strip()

        if choice == "1":
            print_usb_guide()
        elif choice == "2":
            print_wifi_guide()
        else:
            print("无效选择")

        print()
        print("连接后重新运行: python phone_setup.py")


if __name__ == "__main__":
    main()
