import random
import time

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def mobile():
    # 1. 读取关键词
    with open("keywords.txt", "r", encoding="utf-8") as f:
        keywords = [w.strip() for w in f if w.strip()]

    # 2. 配置 EdgeOptions：模拟移动端（iPhone X）
    mobile_emulation = {"deviceName": "iPhone X"}
    options = webdriver.EdgeOptions()
    options.use_chromium = True
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    # （可选）隐藏“受自动化软件控制”提示
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Edge(
        service=EdgeService(EdgeChromiumDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 10)

    try:
        for i in range(1, 31):
            # 3. 打开移动端 Bing 首页
            driver.get("https://www.bing.com")

            # 4. 定位移动端搜索框，输入关键词并回车
            #    Bing Mobile 上搜索框也使用 id="sb_form_q"
            search_box = wait.until(EC.presence_of_element_located((By.ID, "sb_form_q")))
            search_box.clear()
            kw = random.choice(keywords)
            search_box.send_keys(kw, Keys.ENTER)
            print(f"[{i}/30] 搜索关键词：{kw}")

            # 5. 等待结果加载
            wait.until(EC.presence_of_element_located((By.ID, "b_content")))
            time.sleep(random.uniform(1.5, 2.5))

            # 6. 模拟上下滑动（中部 → 底部 → 顶部）
            height = driver.execute_script("return document.body.scrollHeight")
            mid = height // 2

            driver.execute_script(f"window.scrollTo(0, {mid});")
            time.sleep(random.uniform(1, 1.8))

            driver.execute_script(f"window.scrollTo(0, {height});")
            time.sleep(random.uniform(1, 1.8))

            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 1.8))

    finally:
        driver.quit()
