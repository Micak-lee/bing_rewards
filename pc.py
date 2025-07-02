import random
import time

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def pc():
    # 1. 读取关键词
    with open("keywords.txt", "r", encoding="utf-8") as f:
        keywords = [w.strip() for w in f if w.strip()]

    # 2. 启动 Edge
    options = webdriver.EdgeOptions()
    options.use_chromium = True
    # 去掉“受自动化软件控制”的提示
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Edge(
        service=EdgeService(EdgeChromiumDriverManager().install()),
        options=options
    )
    driver.maximize_window()

    # 等待搜索框的最大时长
    wait = WebDriverWait(driver, 10)

    try:
        for i in range(1, 31):
            # 3. 打开搜索引擎首页
            driver.get("https://www.bing.com")

            # 4. 定位搜索框，输入关键词并回车
            box = wait.until(EC.presence_of_element_located((By.ID, "sb_form_q")))
            box.clear()
            kw = random.choice(keywords)
            box.send_keys(kw, Keys.ENTER)
            print(f"[{i}/30] 搜索：{kw}")

            # 5. 等待搜索结果加载
            wait.until(EC.presence_of_element_located((By.ID, "b_content")))
            time.sleep(random.uniform(1.5, 3.0))

            # 6. 模拟滑动：到中部 → 底部 → 回顶
            height = driver.execute_script("return document.body.scrollHeight")
            mid = height // 2

            driver.execute_script(f"window.scrollTo(0, {mid});")
            time.sleep(random.uniform(1, 2))

            driver.execute_script(f"window.scrollTo(0, {height});")
            time.sleep(random.uniform(1, 2))

            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))

    finally:
        driver.quit()
