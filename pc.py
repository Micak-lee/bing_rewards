import random
import time

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 1. 读取关键词
with open("keywords.txt", "r", encoding="utf-8") as f:
    keywords = [line.strip() for line in f if line.strip()]

# 2. 配置 Edge WebDriver
options = webdriver.EdgeOptions()
options.use_chromium = True
# options.add_argument("--headless")  # 如需无头模式，取消注释

driver = webdriver.Edge(
    service=EdgeService(EdgeChromiumDriverManager().install()),
    options=options
)

try:
    # 3. 随机搜索 20 次
    for i in range(20):
        kw = random.choice(keywords)
        search_url = f"https://www.bing.com/search?q={kw}"
        driver.get(search_url)
        print(f"[{i+1}/20] Searching for: {kw}")
        time.sleep(2)  # 等待页面加载，可根据网速调整

finally:
    # 4. 关闭浏览器
    driver.quit()
