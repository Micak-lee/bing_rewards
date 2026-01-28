import pc
import mobile

if __name__ == "__main__":
    # 获取用户输入
    try:
        user_input = input("请输入pc端要自动抓取并搜索的次数 (n): ")
        n1 = int(user_input)
        if n1 < 0:
            print("请输入大于0的整数，默认执行30次。")
            n1 = 30
    except ValueError:
        print("输入无效，默认执行 30 次。")
        n1 = 30

    try:
        user_input = input("请输入移动端自动抓取并搜索的次数 (n): ")
        n2 = int(user_input)
        if n2 < 0:
            print("请输入大于0的整数，默认执行20次。")
            n2 = 20
    except ValueError:
        print("输入无效，默认执行 20 次。")
        n2 = 20

    print(f"任务开始：即将执行 {n1} 次搜索...")
    if n1>0:
        pc.pc(n1)

    print(f"任务开始：即将执行 {n2} 次移动端搜索...")
    if n2>0:
        mobile.mobile(n2)
