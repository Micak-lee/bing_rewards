# Microsoft Rewards Auto-Farming

自动完成 Microsoft Rewards 积分任务，包括 Bing 搜索、每日活动、以及手机 Bing app 的"阅读以赚取"（3分/篇，每日上限30分）。

## 功能

- **Bing PC 搜索** — 模拟桌面端搜索
- **Bing 移动端搜索** — 伪造手机 User-Agent
- **每日活动** — 自动完成投票(poll)、测验(quiz)、更多活动
- **手机 Bing app 阅读以赚取** — 通过 ADB 连接真实 Android 手机，自动进入首页文章阅读，每篇3分
- **登录持久化** — 首次登录后后续自动运行
- **反检测** — 随机延迟、隐藏自动化标志、移除浏览器横幅

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

## 手机连接指南

"阅读以赚取"功能需要通过 ADB 连接 Android 手机。

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

## 文件结构

```
D:\new_bing\
├── main.py              # 主入口（命令行参数：--read-only, --no-read）
├── phone_setup.py       # 手机 ADB 连接助手
├── config.yaml          # 配置文件
├── config.py            # 配置加载
├── browser.py           # 浏览器管理（持久化登录）
├── search.py            # Bing 搜索（PC + 移动端 UA 伪装）
├── dashboard.py         # Rewards 面板信息
├── activities.py        # 每日活动处理
├── mobile_app.py        # 手机 Bing app ADB 自动化
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
