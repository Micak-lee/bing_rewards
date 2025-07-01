import random
import time

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 1. 读取关键词
with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip() for line in f if line.strip()]

# 2. 配置 Edge 浏览器移动端模拟
mobile_emulation = { "deviceName": "iPhone X" }
options = webdriver.EdgeOptions()
options.use_chromium = True
options.add_experimental_option("mobileEmulation", mobile_emulation)

# 如果想自定义 UA 字符串，可以使用：
# ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
#       "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 "
#       "Mobile/15E148 Safari/604.1")
# options.add_argument(f"user-agent={ua}")

driver = webdriver.Edge(
    service=EdgeService(EdgeChromiumDriverManager().install()),
    options=options
)

try:
    # 3. 随机执行 20 次搜索
    for i in range(1, 21):
        kw = random.choice(keywords)
        search_url = f"https://www.bing.com/search?q={kw}"
        driver.get(search_url)
        print(f"[{i}/20] 搜索关键词：{kw}")
        # 根据网络情况可调整等待时间
        time.sleep(2)

finally:
    # 4. 关闭浏览器
    driver.quit()
