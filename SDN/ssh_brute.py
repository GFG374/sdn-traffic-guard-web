#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH暴力破解攻击脚本（SSH Brute Force Attack）

功能：模拟攻击者对SSH服务（22端口）进行暴力破解尝试

检测原理：
- 60秒内访问22端口次数 > 50

RYU控制器检测逻辑：
  SDN/sdn_smart.py 第763-779行
  if dst_port == 22 and conns > 50 (in 60 seconds):
      限速256 kbps + 记录异常
"""

from scapy.all import *
import threading
import time
import argparse
import random

def ssh_brute_force(target_ip='192.168.1.200', src_ip='192.168.1.101', threads=8, duration=60, rate=200):
    """
    SSH暴力破解攻击
    
    Args:
        target_ip: 目标IP地址
        src_ip: 源IP地址（攻击者IP）
        threads: 线程数
        duration: 攻击持续时间（秒）
        rate: 每秒连接尝试次数
    """
    
    stop_flag = threading.Event()
    stats = {'total_attempts': 0, 'lock': threading.Lock()}
    
    def brute_force_thread():
        """单个暴力破解线程"""
        while not stop_flag.is_set():
            try:
                # 构造TCP SYN包（模拟SSH连接尝试）
                src_port = random.randint(1024, 65535)
                
                ip = IP(src=src_ip, dst=target_ip)
                tcp_syn = TCP(sport=src_port, dport=22, flags='S')
                pkt = ip / tcp_syn
                
                # 发送数据包
                send(pkt, verbose=0)
                
                # 更新统计
                with stats['lock']:
                    stats['total_attempts'] += 1
                
                # 控制速率
                time.sleep(1.0 / (rate / threads))
                
            except Exception as e:
                print(f"[错误] {e}")
    
    def monitor_thread():
        """监控线程，打印统计信息"""
        start_time = time.time()
        last_count = 0
        
        while not stop_flag.is_set():
            time.sleep(10)  # 每10秒打印一次
            
            elapsed = time.time() - start_time
            current_count = stats['total_attempts']
            
            # 计算速率
            current_rate = (current_count - last_count) / 10
            avg_rate = current_count / elapsed if elapsed > 0 else 0
            
            print(f"[{int(elapsed)}s] 总尝试: {current_count} | 当前速率: {current_rate:.1f} pps | 平均速率: {avg_rate:.1f} pps")
            
            last_count = current_count
    
    print(f"{'='*60}")
    print(f"🔐 SSH暴力破解攻击启动")
    print(f"{'='*60}")
    print(f"攻击者IP: {src_ip}")
    print(f"目标IP:   {target_ip}")
    print(f"目标端口: 22 (SSH)")
    print(f"线程数:   {threads}")
    print(f"目标速率: {rate} pps")
    print(f"持续时间: {duration} 秒")
    print(f"{'='*60}\n")
    
    # 启动攻击线程
    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=brute_force_thread)
        t.daemon = True
        threads_list.append(t)
        t.start()
        print(f"[线程{i+1}] 已启动，目标速率: {rate//threads} pps")
    
    # 启动监控线程
    monitor = threading.Thread(target=monitor_thread)
    monitor.daemon = True
    monitor.start()
    
    # 等待指定时间
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\n[中断] 用户停止攻击")
    
    # 停止所有线程
    stop_flag.set()
    for t in threads_list:
        t.join(timeout=1)
    
    print(f"\n{'='*60}")
    print(f"✅ SSH暴力破解攻击结束")
    print(f"{'='*60}")
    print(f"总尝试次数: {stats['total_attempts']}")
    print(f"平均速率:   {stats['total_attempts']/duration:.1f} pps")
    print(f"{'='*60}")
    print(f"\n💡 预期RYU控制器检测结果:")
    print(f"   - 异常类型: SSH Brute Force")
    print(f"   - 限速措施: 256 kbps")
    print(f"   - 检测条件: 60秒内22端口连接数>50")
    print(f"   - ✅ 会写入attack_sessions表")
    print(f"   - ✅ 大约10-15秒内触发！")


def dictionary_attack(target_ip, src_ip='192.168.1.200', username='root', password_file=None):
    """
    字典攻击模式（模拟真实SSH暴力破解）
    
    Args:
        target_ip: 目标IP
        src_ip: 源IP
        username: 用户名
        password_file: 密码字典文件
    """
    # 默认密码列表
    default_passwords = [
        'password', '123456', 'admin', 'root', '12345678',
        'qwerty', 'abc123', 'password123', 'admin123', '1234',
        'letmein', 'welcome', 'monkey', '1234567890', 'password1'
    ] * 10  # 重复以达到检测阈值
    
    # 读取密码字典（如果提供）
    if password_file:
        try:
            with open(password_file, 'r') as f:
                passwords = [line.strip() for line in f.readlines()]
        except:
            print(f"[警告] 无法读取密码文件，使用默认密码列表")
            passwords = default_passwords
    else:
        passwords = default_passwords
    
    print(f"{'='*60}")
    print(f"📖 SSH字典攻击模式")
    print(f"{'='*60}")
    print(f"目标: {target_ip}:22")
    print(f"用户名: {username}")
    print(f"密码数量: {len(passwords)}")
    print(f"{'='*60}\n")
    
    attempt_count = 0
    start_time = time.time()
    
    for idx, password in enumerate(passwords):
        try:
            # 构造TCP SYN包（模拟SSH连接）
            src_port = random.randint(1024, 65535)
            
            ip = IP(src=src_ip, dst=target_ip)
            tcp_syn = TCP(sport=src_port, dport=22, flags='S')
            pkt = ip / tcp_syn / Raw(load=f"{username}:{password}")
            
            # 发送数据包
            send(pkt, verbose=0)
            
            attempt_count += 1
            
            # 每10次尝试打印一次
            if (idx + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = attempt_count / elapsed if elapsed > 0 else 0
                print(f"[尝试{attempt_count}] 用户名: {username} | 密码: {password:15s} | 速率: {rate:.1f} pps")
            
            # 控制速率（避免过快）
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            print("\n[中断] 用户停止攻击")
            break
        except Exception as e:
            print(f"[错误] {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ 字典攻击结束")
    print(f"{'='*60}")
    print(f"总尝试次数: {attempt_count}")
    print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SSH暴力破解攻击脚本')
    parser.add_argument('--target', '-t', default='192.168.1.200', help='目标IP地址（默认H8）')
    parser.add_argument('--src', '-s', default='192.168.1.101', help='源IP地址（攻击者，默认H2）')
    parser.add_argument('--threads', '-n', type=int, default=8, help='线程数')
    parser.add_argument('--duration', '-d', type=int, default=60, help='政击持续时间（秒）')
    parser.add_argument('--rate', '-r', type=int, default=200, help='目标速率（pps）')
    parser.add_argument('--dictionary', '-D', action='store_true', help='使用字典攻击模式')
    parser.add_argument('--username', '-u', default='root', help='用户名（字典模式）')
    parser.add_argument('--password-file', '-p', help='密码字典文件路径')
    
    args = parser.parse_args()
    
    try:
        if args.dictionary:
            # 字典攻击模式
            dictionary_attack(
                target_ip=args.target,
                src_ip=args.src,
                username=args.username,
                password_file=args.password_file
            )
        else:
            # 高速暴力破解模式
            ssh_brute_force(
                target_ip=args.target,
                src_ip=args.src,
                threads=args.threads,
                duration=args.duration,
                rate=args.rate
            )
    except KeyboardInterrupt:
        print("\n\n[中断] 用户停止攻击")
    except Exception as e:
        print(f"\n[错误] {e}")

"""
使用示例：

1. 默认攻击（H2 攻击 H8，200 pps，60秒）：
   sudo python3 ssh_brute.py

2. 高速攻击（300 pps）：
   sudo python3 ssh_brute.py -r 300 -n 10

3. 字典攻击模式：
   sudo python3 ssh_brute_force.py -t 192.168.1.100 -s 192.168.1.200 --dictionary -u admin

4. 使用自定义密码字典：
   sudo python3 ssh_brute_force.py -t 192.168.1.100 -s 192.168.1.200 -D -p /path/to/passwords.txt

在Mininet中使用：
   mininet> h2 python3 ssh_brute.py &

注意：
- ✅ 默认配置：H2(192.168.1.101) 攻击 H8(192.168.1.200)
- ✅ RYU检测阈值：60秒内>50次连接
- ✅ 默认200pps，大约10-15秒就会触发检测
- ✅ 会自动写入attack_sessions表
"""

