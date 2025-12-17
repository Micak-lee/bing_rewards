import random
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


def get_robust_keywords(driver):
    """
    功能：在移动端模式下获取关键词
    策略：Bing新闻(5秒限时) -> 百度热搜 -> 本地词库
    """
    keywords = []
    print("正在获取移动端热门搜索内容...")

    # --- 阶段 1: 尝试从 Bing 新闻获取 (极速模式) ---
    try:
        # 临时设置极短超时 (5秒)
        driver.set_page_load_timeout(5)

        try:
            driver.get("https://www.bing.com/news")
        except:
            # 移动端页面很重，超时是预期的，直接强制停止加载
            driver.execute_script("window.stop();")

        time.sleep(1)  # 给DOM一点渲染时间

        # 移动端结构复杂，直接抓取所有可见的链接文本
        elements = driver.find_elements(By.TAG_NAME, "a")

        for e in elements:
            txt = e.text.strip()
            # 过滤逻辑：去掉太短的、功能性按钮(如"登录")
            if len(txt) > 4 and "Microsoft" not in txt and "Sign in" not in txt:
                if txt not in keywords:
                    keywords.append(txt)

        print(f"Bing 移动版抓取结果: {len(keywords)} 个词")

    except Exception as e:
        print(f"Bing 抓取跳过: {e}")
    finally:
        # 恢复较长的超时时间，保证后续搜索正常
        driver.set_page_load_timeout(20)

    # --- 阶段 2: 百度热搜补位 ---
    if len(keywords) < 10:
        print("关键词不足，切换至百度热搜补位...")
        try:
            driver.get("https://top.baidu.com/board?tab=realtime")
            # 百度移动端页面结构可能变化，使用通用抓取
            time.sleep(2)
            elements = driver.find_elements(By.TAG_NAME, "div")  # 百度移动端标题常在 div 中

            for e in elements:
                txt = e.text.strip()
                # 百度热搜通常比较长，且不包含换行
                if len(txt) > 5 and len(txt) < 23 and "\n" not in txt:
                    if txt not in keywords and "搜索" not in txt:
                        keywords.append(txt)
                        if len(keywords) >= 35:
                            break
        except Exception as e:
            print(f"百度补位异常: {e}")

    # --- 阶段 3: 本地兜底 (绝对稳健) ---
    if len(keywords) < 23:
        print("网络抓取受限，使用本地精选词库...")
        backup = [
            "2024年热门手机排行榜", "杭州亚运会精彩瞬间", "健康减脂食谱推荐",
            "新能源汽车补贴政策", "Python编程入门教程", "适合周末旅游的城市",
            "高分悬疑电影推荐", "社保卡如何在线办理", "今日黄金价格走势",
            "如何提高睡眠质量", "办公室颈椎病预防", "最新的科幻小说",
            "世界杯足球赛程", "华为Mate60评测", "ChatGPT使用技巧",
            "家庭红烧肉的做法", "春季流感预防指南", "个人所得税退税流程",
            "这周天气预报查询", "经典老歌排行榜", "王者荣耀最新攻略",
            "考公面试热点话题", "装修风格效果图", "猫咪掉毛怎么解决",
            "笔记本电脑性价比", "空气炸锅美食食谱", "练出马甲线的动作",
            "最近比较火的电视剧", "高铁抢票攻略", "世界未解之谜"
        ]
        for w in backup:
            if w not in keywords:
                keywords.append(w)

    # 截取前23个
    final_keywords = keywords[:23]
    print(f"最终生成移动端任务: {len(final_keywords)} 个关键词")
    return final_keywords


def mobile():
    # --- 1. 配置 Edge 移动端模拟 ---
    mobile_emulation = {"deviceName": "iPhone X"}

    options = webdriver.EdgeOptions()
    options.use_chromium = True
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # [关键] 设置加载策略为 eager (DOM加载完即算完成)
    options.page_load_strategy = 'eager'

    edge_driver_path = "edgedriver_win64/msedgedriver.exe"

    try:
        service = EdgeService(executable_path=edge_driver_path)
        driver = webdriver.Edge(service=service, options=options)
    except Exception:
        print("未找到指定驱动，尝试使用默认驱动...")
        driver = webdriver.Edge(options=options)

    # 设置全局强制超时 (防止搜索时卡死)
    driver.set_page_load_timeout(15)

    wait = WebDriverWait(driver, 10)

    try:
        # --- 2. 获取关键词 ---
        keywords = get_robust_keywords(driver)

        # --- 3. 循环搜索 ---
        for i in range(1, 24):
            kw = keywords[i - 1]

            try:
                # 尝试打开页面
                driver.get("https://www.bing.com")
            except TimeoutException:
                # 如果 Bing 首页加载超时，强制停止并尝试继续操作
                # print("首页加载超时，尝试直接搜索...")
                driver.execute_script("window.stop();")
            except Exception as e:
                print(f"[{i}/23] 连接错误: {e}")
                continue

            try:
                # 定位搜索框 (Bing Mobile ID 也是 sb_form_q)
                search_box = wait.until(EC.presence_of_element_located((By.ID, "sb_form_q")))
                search_box.clear()

                # 输入并搜索
                search_box.send_keys(kw)
                time.sleep(0.1)
                search_box.send_keys(Keys.ENTER)
                print(f"[{i}/23] 移动端搜索：{kw}")

            except Exception as e:
                print(f"[{i}/23] 搜索框定位失败: {e}")
                continue

            # --- 4. 模拟移动端浏览与滑动 ---
            try:
                # 等待结果出现 (最多等5秒)
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "b_content")))

                # 简单滑动，模拟阅读
                driver.execute_script(f"window.scrollTo(0, 500);")
                time.sleep(random.uniform(1, 2))
                driver.execute_script("window.scrollTo(0, 0);")
            except Exception:
                pass  # 忽略滑动错误

            # --- 5. 随机等待 (5-10秒) ---
            wait_time = random.uniform(5, 10)
            time.sleep(wait_time)

    finally:
        try:
            driver.quit()
        except:
            pass
        print("移动端任务结束，程序退出。")


if __name__ == "__main__":
    mobile()