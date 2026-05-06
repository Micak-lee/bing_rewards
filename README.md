# Microsoft Rewards Auto-Farming

自动完成 Microsoft Rewards 积分任务，包括 Bing 搜索和每日活动。

## 功能

- **Bing PC 搜索** — 模拟桌面端搜索获取积分
- **Bing 移动端搜索** — 伪造手机 User-Agent 获取移动端积分
- **每日活动** — 自动完成投票(poll)、测验(quiz)和更多活动(more activities)
- **测验答题** — 通过 Bing 搜索题干自动查找答案
- **登录持久化** — 首次手动登录后，后续运行自动登录
- **可见浏览器** — Edge 浏览器窗口可见，随时了解运行状态
- **反检测** — 随机延迟、`navigator.webdriver` 隐藏、移除自动化横幅

## 安装

```powershell
# 1. 克隆仓库
git clone git@github.com:Micak-lee/bing_rewards.git
cd bing_rewards

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Chromium 浏览器
python -m playwright install chromium
```

## 使用

```powershell
python main.py
```

**首次运行：**
1. Edge 浏览器窗口会自动打开
2. 手动登录你的 Microsoft 账号
3. 回到命令行按 ENTER 继续
4. 程序自动执行搜索和每日活动

**后续运行：** 自动登录，无需手动操作。

## 配置

编辑 `config.yaml` 根据需要调整参数：

```yaml
search:
  pc_count: 30          # PC 搜索次数
  mobile_count: 20      # 移动端搜索次数
  min_delay: 3.0        # 搜索最小间隔（秒）
  max_delay: 8.0        # 搜索最大间隔（秒）

activities:
  enabled: true         # 是否执行每日活动
  poll_choice: "random" # 投票选项：random/first/last

browser:
  channel: "msedge"     # 浏览器：msedge/chrome/chromium
  headless: false       # 是否无头模式
```

## 文件结构

```
bing_rewards/
├── main.py              # 主入口
├── config.yaml          # 配置文件
├── config.py            # 配置加载
├── browser.py           # 浏览器管理（持久化登录）
├── search.py            # Bing 搜索（PC + 移动端）
├── dashboard.py         # Rewards 面板交互
├── activities.py        # 每日活动处理
├── queries.py           # 随机搜索词生成
├── logger.py            # 日志模块
├── utils.py             # 工具函数
├── requirements.txt     # 依赖
└── queries/
    ├── zh_keywords.txt  # 中文关键词库
    └── en_keywords.txt  # 英文关键词库
```

## 免责声明

本项目仅供学习交流使用。自动获取 Microsoft Rewards 积分可能违反微软服务条款，使用风险自负。建议使用小号测试，避免主账号受到影响。
