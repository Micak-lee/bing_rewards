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
    功能：极速获取关键词。
    策略：优先 Bing 新闻 (限时5秒)，失败或数量少则立刻切换百度热搜。
    """
    keywords = []

    # --- 阶段 1: 尝试从 Bing 新闻获取 (快速模式) ---
    print("正在尝试获取 Bing 新闻 (限时5秒)...")

    # 保存原始的超时设置，以便恢复
    original_timeout = driver.timeouts.page_load

    try:
        # 1. 设置极短的超时时间，防止卡死
        driver.set_page_load_timeout(5)

        try:
            driver.get("https://www.bing.com/news")
        except:
            # 超时是预期的，因为我们设置了 eager/5秒，
            # 只要页面大致出来了就行，直接停止加载
            driver.execute_script("window.stop();")

        # 2. 稍微等一下 DOM 渲染
        time.sleep(1)

        # 3. 尝试多种选择器抓取标题
        # Bing 新闻结构复杂，尝试抓取所有含有文本的链接，稍后通过长度过滤
        elements = driver.find_elements(By.TAG_NAME, "a")

        for e in elements:
            # 只要显示的文本
            txt = e.text.strip()
            # 过滤逻辑：长度大于4，且不包含常见功能词
            if len(txt) > 4 and "Microsoft" not in txt and "反馈" not in txt:
                if txt not in keywords:
                    keywords.append(txt)

        print(f"Bing 新闻抓取结果: {len(keywords)} 个词")

    except Exception as e:
        print(f"Bing 新闻抓取跳过: {e}")
    finally:
        # 恢复正常的超时时间 (比如 15-20秒)，以免影响后续搜索
        driver.set_page_load_timeout(20)

    # --- 阶段 2: 智能补位 (百度热搜) ---
    # 如果 Bing 抓取失败，或者抓取的词太少 (比如那个只抓到1个的情况)
    if len(keywords) < 10:
        print("关键词来源不稳定或数量不足，切换至百度热搜极速版...")
        try:
            driver.get("https://top.baidu.com/board?tab=realtime")
            # 百度热搜是纯文本列表，加载非常快，不需要复杂等待
            wait = WebDriverWait(driver, 5)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".c-single-text-ellipsis")))

            elements = driver.find_elements(By.CSS_SELECTOR, ".c-single-text-ellipsis")
            for e in elements:
                text = e.text.strip()
                if len(text) > 2 and text not in keywords:
                    keywords.append(text)
                    # 凑够 35 个就停，不用全部抓
                    if len(keywords) >= 35:
                        break
        except Exception as e:
            print(f"百度热搜获取异常: {e}")

    # --- 阶段 3: 本地兜底 ---
    # 万一断网或所有网站都改版了
    if len(keywords) < 30:
        print("网络获取受阻，使用本地词库...")
        backup = [
            "人工智能发展", "Python自动化", "今日天气", "杭州亚运会", "新能源汽车",
            "健康饮食习惯", "很多人的选择", "旅游景点推荐", "最新的电影", "股票市场分析",
            "房价走势", "手机新款评测", "考研复习资料", "公务员考试", "热门小说排行榜",
            "减肥食谱", "健身计划", "家常菜做法", "最近的新闻", "科技前沿",
            "火星探测", "量子计算", "区块链技术", "虚拟现实设备", "自动驾驶汽车",
            "环保低碳生活", "垃圾分类标准", "心理健康咨询", "急救小常识", "法律咨询服务"
        ]
        for w in backup:
            if w not in keywords:
                keywords.append(w)

    # 最终切片
    final_keywords = keywords[:30]
    print(f"最终生成任务列表: {len(final_keywords)} 个关键词")
    return final_keywords


def pc():
    options = webdriver.EdgeOptions()
    options.use_chromium = True
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # --- 关键修改 1: 页面加载策略改为 eager ---
    # none: 完全不等待; eager: DOM加载完就继续; normal: 等待所有资源(默认)
    options.page_load_strategy = 'eager'

    edge_driver_path = "edgedriver_win64/msedgedriver.exe"

    try:
        service = EdgeService(executable_path=edge_driver_path)
        driver = webdriver.Edge(service=service, options=options)
    except Exception:
        print("尝试使用默认驱动...")
        driver = webdriver.Edge(options=options)

    driver.maximize_window()

    # --- 关键修改 2: 设置全局页面加载超时时间 ---
    # 如果15秒没加载完，强行停止加载，防止 disconnect
    driver.set_page_load_timeout(15)

    wait = WebDriverWait(driver, 10)

    try:
        keywords = get_robust_keywords(driver)
        print(f"已准备好 {len(keywords)} 个搜索任务。")

        for i in range(1, 31):
            kw = keywords[i - 1]

            try:
                # 尝试打开页面
                driver.get("https://www.bing.com")
            except TimeoutException:
                # 如果加载超时，打印一下，但在 eager 模式下通常意味着元素已经出来了，只是还在转圈
                # 我们直接发送 'window.stop()' 强制浏览器停止转圈
                print(f"[{i}/30] 页面加载超时，强制停止加载并继续...")
                try:
                    driver.execute_script("window.stop();")
                except:
                    pass
            except WebDriverException as e:
                # 捕捉 Connection timed out
                print(f"[{i}/30] 发生连接错误，跳过: {e}")
                continue

            # 搜索操作
            try:
                # 即使页面没加载完，只要搜索框出来了就行
                box = wait.until(EC.presence_of_element_located((By.ID, "sb_form_q")))
                box.clear()
                box.send_keys(kw)
                time.sleep(0.2)
                box.send_keys(Keys.ENTER)
                print(f"[{i}/30] 搜索：{kw}")

            except Exception as e:
                print(f"[{i}/30] 搜索框交互失败: {e}")
                continue

            # 简单的防风控浏览
            try:
                # 等待内容出现，最多等5秒，等不到就算了
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "b_content")))
                driver.execute_script("window.scrollTo(0, 500);")
            except:
                pass

                # 随机等待
            time.sleep(random.uniform(5, 10))

    except Exception as main_e:
        print(f"程序发生严重错误: {main_e}")
    finally:
        try:
            driver.quit()
        except:
            pass
        print("程序结束。")


if __name__ == "__main__":
    pc()