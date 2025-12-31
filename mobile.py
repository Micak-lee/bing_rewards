import random
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


def get_robust_keywords(driver, target_count):
    """
    功能：在移动端/PC端通用获取关键词
    修复：使用 JS 抓取替代 Selenium 元素遍历，彻底解决 StaleElementReferenceException
    """
    keywords = []
    print(f"正在获取搜索任务 (目标: {target_count} 个)...")

    # --- 阶段 1: 尝试从 Bing 新闻获取 (JS 抓取版) ---
    try:
        driver.set_page_load_timeout(10)  # 稍微放宽一点时间

        try:
            driver.get("https://www.bing.com/news")
        except:
            driver.execute_script("window.stop();")

        time.sleep(1.5)  # 等待 JS 渲染文本

        # [核心修复] 使用 JavaScript 一次性提取所有 a 标签文本
        # 这避免了在 Python 循环中页面刷新导致的 "Stale Element" 错误
        raw_texts = driver.execute_script("""
            var texts = [];
            var links = document.getElementsByTagName("a");
            for (var i = 0; i < links.length; i++) {
                var t = links[i].innerText || links[i].textContent;
                if (t && t.length > 4) {
                    texts.push(t);
                }
            }
            return texts;
        """)

        if raw_texts:
            for txt in raw_texts:
                txt = txt.strip()
                # 过滤逻辑
                if "Microsoft" not in txt and "Sign in" not in txt and "反馈" not in txt:
                    if txt not in keywords:
                        keywords.append(txt)
                        if len(keywords) >= target_count + 5:
                            break

        print(f"Bing 抓取结果: {len(keywords)} 个词")

    except Exception as e:
        print(f"Bing 抓取跳过: {e}")
    finally:
        driver.set_page_load_timeout(20)

    # --- 阶段 2: 百度热搜补位 ---
    if len(keywords) < target_count:
        print("关键词不足，切换至百度热搜补位...")
        try:
            driver.get("https://top.baidu.com/board?tab=realtime")
            time.sleep(2)

            # 同样使用 JS 抓取百度，防止百度也报错
            baidu_texts = driver.execute_script("""
                var texts = [];
                // 尝试抓取常见的标题类名或直接抓 div/a
                var els = document.querySelectorAll('.c-single-text-ellipsis, .content_1YWBm a'); 
                for (var i = 0; i < els.length; i++) {
                    texts.push(els[i].innerText);
                }
                return texts;
            """)

            if not baidu_texts:  # 如果上面的选择器没抓到，尝试粗暴抓取
                baidu_texts = driver.execute_script("""
                    var texts = [];
                    var els = document.getElementsByTagName("div");
                    for (var i = 0; i < els.length; i++) {
                        texts.push(els[i].innerText);
                    }
                    return texts;
                """)

            for text in baidu_texts:
                text = text.strip()
                if len(text) > 5 and len(text) < 23 and "\n" not in text:
                    if text not in keywords and "搜索" not in text:
                        keywords.append(text)
                        if len(keywords) >= target_count + 5:
                            break
        except Exception as e:
            print(f"百度补位异常: {e}")

    # --- 阶段 3: 本地兜底 (循环补足) ---
    if len(keywords) < target_count:
        print("网络抓取受限，使用本地精选词库循环补足...")
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

        backup_index = 0
        while len(keywords) < target_count:
            word = backup[backup_index % len(backup)]
            if word not in keywords:
                keywords.append(word)
            else:
                keywords.append(f"{word} {random.randint(1, 100)}")
            backup_index += 1

    final_keywords = keywords[:target_count]
    print(f"最终生成任务: {len(final_keywords)} 个关键词")
    return final_keywords


def mobile(search_num):
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
        # --- 2. 获取关键词 (传入用户设定的数量) ---
        keywords = get_robust_keywords(driver, search_num)
        real_count = len(keywords)

        # --- 3. 循环搜索 ---
        for i in range(1, real_count + 1):
            kw = keywords[i - 1]

            try:
                # 尝试打开页面
                driver.get("https://www.bing.com")
            except TimeoutException:
                # 如果 Bing 首页加载超时，强制停止并尝试继续操作
                driver.execute_script("window.stop();")
            except Exception as e:
                print(f"[{i}/{real_count}] 连接错误: {e}")
                continue

            try:
                # 定位搜索框 (Bing Mobile ID 也是 sb_form_q)
                search_box = wait.until(EC.presence_of_element_located((By.ID, "sb_form_q")))
                search_box.clear()

                # 输入并搜索
                search_box.send_keys(kw)
                time.sleep(0.1)
                search_box.send_keys(Keys.ENTER)
                print(f"[{i}/{real_count}] 移动端搜索：{kw}")

            except Exception as e:
                print(f"[{i}/{real_count}] 搜索框定位失败: {e}")
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
    # 获取用户输入
    try:
        user_input = input("请输入移动端自动抓取并搜索的次数 (n): ")
        n = int(user_input)
        if n <= 0:
            print("请输入大于0的整数，默认执行20次。")
            n = 20
    except ValueError:
        print("输入无效，默认执行 20 次。")
        n = 20

    print(f"任务开始：即将执行 {n} 次移动端搜索...")
    mobile(n)