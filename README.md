# Microsoft Rewards Auto-Farming

自动完成 Microsoft Rewards 积分任务：Bing 搜索、每日活动，以及手机必应 App 的「阅读以赚取」（3 分/篇，每日上限 30 分）。

「阅读以赚取」有**两套互不冲突的实现**，按场合选用：

| 方案 | 需要什么 | 适合 |
|---|---|---|
| **A. 手机 App「必应阅读助手」**（推荐） | 只要手机，不用电脑、不用 ADB、不用 root | 日常刷分 |
| **B. 电脑脚本 + ADB 遥控手机** | 电脑常开 + 手机 USB/WiFi 连着 + 必应 App 在前台 | 已配好 ADB、想跟搜索任务一起跑 |

---

# 一、手机 App「必应阅读助手」（推荐）

装在手机上的原生 Android 应用：点一下「开始」，它在必应 App 里自动逐条打开新闻 → 滑动阅读 → 返回，读完自动去奖励页核对积分。

> 详细文档见 [`android/README.md`](android/README.md)

## 安装

APK：[`必应阅读助手-v1.0.apk`](必应阅读助手-v1.0.apk)（8.93 MB，可直接传到手机点击安装）

```powershell
# 或者用数据线安装
adb install -r "D:\new_bing\必应阅读助手-v1.0.apk"
```

## 开启无障碍服务（必做一次，之后就不需要电脑了）

> ⚠️ **本应用是侧载安装（不是从应用市场装的），Android 13+ 与荣耀 MagicOS 会因此限制它的无障碍权限。**
> 用 adb 强行写入的"已启用"会被系统收回，表现为：无障碍设置里开关明明显示"已开启"，App 里却提示未开启，插着电脑能用、拔了线就不能用。
> 正确做法是按下面四步在手机上手动开一次。

1. **允许受限设置**（只需做一次）
   设置 → 应用 → 应用管理 → 必应阅读助手 → 右上角 **⋮** → **允许受限设置**
   （App 里的「应用信息」按钮会直接跳到这一页；看不到 ⋮ 说明已允许过，跳过）

2. **开启无障碍**
   设置 → 无障碍 → 已安装的服务 → **必应阅读助手** → 打开开关 → 弹窗点「确定」
   ⚠️ 若它显示"已开启"但 App 仍提示未开启：**把开关关掉，再打开一次**。

3. **电池白名单**
   App 里的「电池白名单」按钮 → 允许。
   荣耀再补一步：设置 → 应用 → 必应阅读助手 → 耗电管理 → **允许后台活动**。

4. **回到 App**，状态变绿后就能用了。

App 内置了这三件事的入口与图文步骤（状态卡片上的「应用信息 / 无障碍设置 / 电池白名单 / 图文步骤」按钮），状态不对时还会直接告诉你差哪一步。

做完之后：**拔线、重启手机都不影响**。App 还带一个常驻前台服务（一条低优先级通知"待命中"），避免进程被系统回收导致无障碍掉线。

### 如果哪天又变成"未开启"

荣耀在系统清理后台时可能把侧载应用的无障碍服务摘掉，重新按上面第 2 步开一次即可（App 会检测到并给出提示）。
若状态卡片出现 ⚠️ 提示"系统限制了侧载应用"，说明第 1 步的允许被重置了（例如重装 App），补做第 1 步。


## 使用

1. 确认必应 App 已登录微软账号；
2. 打开「必应阅读助手」，按需调整参数（默认 12 篇 / 停留 10 秒 / 滑动 3 次 / 间隔 1500 毫秒）；
3. 点 **开始刷阅读**，然后把手机放一边——运行期间 App 会申请**屏幕常亮**（调暗但不清屏），因为屏幕一灭手势就失效。

它会先自己走一遍「主页 → 左上角头像 → Microsoft Rewards」读今天的进度：

- 已经 **30/30** → 直接结束，不做无用功；
- 没满 → 进新闻流逐条阅读，结束后再读一次进度，日志里给出 `15 → 30（本次 +15）`。

**不想查、直接开刷**？点旁边的「**直接刷（跳过检查）**」——不做任何查询，立刻进阅读流程（今天满了也照读）。

**查进度很快**：状态卡片上常驻显示「今日阅读积分 30/30 已满，不用再读」，也有「查进度」按钮随时刷新。实测一次真实查询约 **1.9 秒**（原来固定等待要 17 秒），当天已满或 3 分钟内查过时直接走本地缓存，**0.0 秒**返回。

界面上的 **抓取界面** 会把当前必应控件树存到
`/sdcard/Android/data/com.musle.bingreader/files/dump_*.txt`，**导出** 保存运行日志——必应改版导致找不到文章时，把它们发我即可改选择器。

## 实测结果（2026-10-01，荣耀 AAP-AN00 / Android 16 / MagicOS 10 / 必应 32.6）

| 指标 | 运行前 | 运行后 |
|---|---|---|
| 奖励页「阅读以赚取」 | 已赚取 **15** 积分（需要 30） | 已赚取 **30 积分**（满额） |
| 头像面板总积分 | 7,550 | **7,565（+15）** |
| 今日积分 | 105/120 | **120/120** |

**查进度耗时**（同一台手机实测）：

| | 改造前 | 改造后 |
|---|---|---|
| 真实查询一次 | ~17 秒 | **1.9 秒** |
| 当天已满 / 3 分钟内查过 | ~17 秒 | **0.0 秒**（本地缓存） |


连续 11 篇的日志节选（`adb logcat -s BingReader`）：

```
任务开始：目标 10 篇，每篇停留 10s、滑动 3 次
已进入新闻流，开始逐条阅读
第 1 篇：「亚运最新排名出炉! 日本183枚、韩国95枚，中国运动健儿太争气」
已读 1 篇
...
已读 11 篇
「阅读以赚取」今日已赚取 30 积分（上限 30）
今日阅读积分已满，无需再读，任务结束
```

## 它是怎么找到文章和进度的

无障碍服务直接读屏 + 模拟手指，不注入、不 hook：

- **入口**：奖励页上 `content-desc` 以「阅读以赚取」开头的可点击 View；
- **文章**：新闻流是 `WebView(desc="MSN")`，每条新闻是 `content-desc` 为标题的可点击 `View`。
  筛选：在 WebView 内、宽 > 屏幕 55%、高 < 屏幕 35%、不在搜索框/底部导航区域、
  文本像一句话（中文 ≥ 6 字或英文 ≥ 12 字母），并排除电话号码/纯数字与带「广告」标记的广告位；
- **是否进了文章**：文章页的 WebView `content-desc` 会变成文章标题；
- **进度**：主页 → 左上角头像 → Microsoft Rewards → 解析「阅读以赚取, 已赚取的 N 积分」。

## 失效与排错

| 现象 | 处理 |
|---|---|
| 点开始提示"请先开启无障碍服务" | 见上文「开启无障碍服务」，注意 **允许受限设置** |
| **明明没满却显示"已满"** | 已修复：读到「已满」会自动刷新奖励页复核一次；缓存只信 2 分钟 |
| 日志："头像面板里没找到 Microsoft Rewards" | 必应改版；程序会自动重试；点「抓取界面」把 dump 发我 |
| 日志："这一屏没有新文章" | 正常收尾，程序会翻页/回主页/恢复布局重找，连续 10 次才结束 |
| 日志："新闻流区域异常：WebView 高度只有屏幕的 xx%" | 必应首页进了"扁塌布局"，程序自动恢复（回主页 + 拉回顶部） |
| 日志："当前前台是 xxx，切回必应" | 点到广告里的电话/商店了，程序已自动切回 |
| 读到一半停了 | 看日志末行；无障碍服务被系统解绑时程序会等 15 秒重连 |
| 想排查任何异常 | 取手机上的 `/sdcard/Android/data/com.musle.bingreader/files/last_run.log`（每次运行自动写，含完整过程） |

> 进度显示的两道保险：① 读到「已满」会**自动刷新奖励页复核**，防止读到 WebView 里隔夜的旧数据（真机上遇到过：页面显示 30，实际新的一天是 0）；② 缓存只信 **2 分钟**，状态卡片会写明 `x/30（07:17 查询）`，一眼能看出数据新不新。

## 重新编译 App

```powershell
# 首次：下载 Gradle + Android SDK（约 400MB，带国内镜像回退）
python D:\new_bing\tools\bootstrap_toolchain.py
python D:\new_bing\tools\install_sdk_manual.py

# 编译（默认先清旧产物；沙箱下旧文件带低完整性标签无法覆盖）
powershell -ExecutionPolicy Bypass -File D:\new_bing\tools\build_apk.ps1

# 编译并安装到手机
powershell -ExecutionPolicy Bypass -File D:\new_bing\tools\build_apk.ps1 -Install -Device <序列号>
```

工程：`android/`（Kotlin + Jetpack Compose，AGP 8.9.2 / Gradle 8.11.1 / Kotlin 2.1.20，compileSdk 35 / minSdk 26）。

---

# 二、电脑脚本（搜索 + 活动 + ADB 遥控阅读）

## 功能

- **Bing PC 搜索** — 模拟桌面端搜索
- **Bing 移动端搜索** — 伪造手机 User-Agent
- **每日活动** — 自动完成投票(poll)、测验(quiz)、更多活动
- **手机阅读以赚取（ADB 方案）** — 通过 ADB 遥控手机必应 App 读首页文章，每篇 3 分
- **登录持久化** — 首次登录后后续自动运行
- **反检测** — 随机延迟、隐藏自动化标志、移除浏览器横幅

> 注意：ADB 方案要求手机**已连接且必应 App 能被遥控**，未连接时该步骤会被跳过（日志 `No Android device detected`），当天这部分积分就拿不到——这也是推荐用手机 App 的原因。

## 安装

```powershell
cd D:\new_bing
pip install -r requirements.txt
python -m playwright install chromium
```

## 使用

```powershell
# 完整流程（搜索 + 活动 + 阅读以赚取）
python main.py

# 仅执行手机"阅读以赚取"
python main.py --read-only

# 跳过"阅读以赚取"，只做搜索+活动
python main.py --no-read

# 手机连接助手
python phone_setup.py
```

运行后按提示输入 PC 搜索次数和移动端搜索次数，直接回车使用默认值。

## 手机连接指南（ADB 方案）

### USB 连接

1. 手机开启「开发者选项」：设置 → 关于手机 → 连续点击「版本号」7 次
2. 开启「USB 调试」：设置 → 系统 → 开发者选项 → USB 调试
3. USB 连接电脑，手机上确认「允许 USB 调试」
4. 运行 `python phone_setup.py` 验证

### WiFi 连接（配合 Phone Link）

1. 手机开启 USB 调试
2. 手机和电脑在同一 WiFi
3. USB 连接一次后运行 `adb tcpip 5555`，拔线
4. 运行 `adb connect <手机IP>:5555`
5. 之后可通过 Phone Link (连接至 Windows) 查看手机画面、手动控制

## 配置

编辑 `config.yaml`：

```yaml
search:
  pc_count: 30          # PC 搜索默认次数
  mobile_count: 20      # 移动端搜索默认次数
  min_delay: 3.0        # 搜索最小间隔（秒）
  max_delay: 8.0        # 搜索最大间隔（秒）

activities:
  enabled: true         # 是否执行每日活动
  poll_choice: "random" # 投票选项：random/first/last

mobile_app:
  enabled: true         # 启用手机阅读以赚取（需 ADB 连接）
  adb_path: "adb"
  read_article_count: 10  # 阅读文章数（上限10篇=30分）
  read_dwell_time: 10     # 每篇文章停留秒数

browser:
  channel: "msedge"    # msedge / chrome / chromium
  headless: false      # true = 无头模式（不可见）
```

---

# 每天 08:00 自动运行（Windows 计划任务）

| 项 | 值 |
|---|---|
| 任务名 | `MicrosoftRewards Daily 0800` |
| 触发 | 每天 08:00，允许电池供电启动、切电池不中断、错过时间补跑 |
| 执行 | `powershell -NoProfile -ExecutionPolicy Bypass -File D:\new_bing\run_daily.ps1 -PcCount 30 -MobileCount 0` |
| 日志 | `logs\daily_YYYY-MM-DD.log` |

`run_daily.ps1` 会把 `30` / `0` 两个答案喂给 `main.py` 的交互提问（PC 搜索 30 次、移动端 0 次）。

```powershell
# 手动测试 / 注册 / 删除
powershell -File D:\new_bing\run_daily.ps1 -DryRun
powershell -File D:\new_bing\run_daily.ps1 -Register
schtasks /Delete /TN "MicrosoftRewards Daily 0800" /F
```

这套任务只做**网页搜索 + 每日活动**；「阅读以赚取」交给手机 App（方案 A）即可，两边都跑也不会重复扣次数——App 会先读进度，满了就不再读。

---

# 文件结构

```
D:\new_bing\
├── 必应阅读助手-v1.0.apk   # 手机 App 安装包（方案 A）
├── android\                # App 工程（Kotlin + Compose）与 android\README.md
│   ├── app\src\main\java\com\musle\bingreader\
│   │   ├── ReaderEngine.kt               # 自动化主流程与选择器规则
│   │   ├── ReaderAccessibilityService.kt # 读屏/手势/窗口枚举/屏幕常亮
│   │   ├── MainActivity.kt               # 界面
│   │   ├── LogBus.kt / NodeDump.kt / Prefs.kt
│   │   └── res\ + AndroidManifest.xml
│   └── keystore\debug.keystore           # 调试签名（放在工程内，避免写用户目录）
├── tools\                  # 编译与调试脚本
│   ├── bootstrap_toolchain.py   # 下载 Gradle + Android cmdline-tools
│   ├── install_sdk_manual.py    # 直连镜像下载并解包 platform/build-tools
│   ├── build_apk.ps1            # 编译（可 -Install 直接装到手机）
│   ├── dump_bing_ui.ps1         # uiautomator 抓必应界面，用于调选择器
│   └── check_points_api.py      # 用 auth_state.json 的 Cookie 读奖励页
├── .toolchain\ .android-sdk\ .gradle-home\   # 编译工具链（约 2GB，可删）
├── main.py              # 主入口（命令行参数：--read-only, --no-read）
├── run_daily.ps1        # 每天 08:00 的包装脚本（喂入 30 / 0）
├── phone_setup.py       # 手机 ADB 连接助手
├── config.yaml          # 配置文件
├── config.py            # 配置加载
├── browser.py           # 浏览器管理（持久化登录）
├── search.py            # Bing 搜索（PC + 移动端 UA 伪装）
├── dashboard.py         # Rewards 面板信息
├── activities.py        # 每日活动处理
├── mobile_app.py        # 手机 Bing app ADB 自动化（方案 B）
├── queries.py           # 随机搜索词生成
├── logger.py            # 日志模块
├── utils.py             # 工具函数
├── requirements.txt     # 依赖
└── queries/
    ├── zh_keywords.txt  # 中文关键词库
    └── en_keywords.txt  # 英文关键词库
```

## 免责声明

本项目仅供学习交流使用。自动获取 Microsoft Rewards 积分可能违反微软服务条款，使用风险自负。
