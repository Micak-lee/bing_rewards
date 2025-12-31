import pc
import mobile

if __name__ == "__main__":
    # 获取用户输入
    try:
        user_input = input("请输入pc端要自动抓取并搜索的次数 (n): ")
        n = int(user_input)
        if n <= 0:
            print("请输入大于0的整数，默认执行30次。")
            n = 30
    except ValueError:
        print("输入无效，默认执行 30 次。")
        n = 30

    print(f"任务开始：即将执行 {n} 次搜索...")
    pc.pc(n)
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
    mobile.mobile(n)
