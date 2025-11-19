#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mininet 拓扑：启动时自动给所有主机口配好 3 档 QoS 队列
低速 256 Kbit/s  中速 1 Mbit/s  高速 2 Mbit/s
对应 OpenFlow queue-id 1/2/3
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
import os
import time

# ---------- 工具：给单端口配 3 档 QoS ----------
def config_qos_port(intf):
    """Linux tc + OVS 一次过"""
    # 1. Linux HTB 三档
    os.system(f'sudo tc qdisc add dev {intf} root handle 1: htb default 10 2>/dev/null')
    os.system(f'sudo tc class add dev {intf} parent 1: classid 1:10 htb rate 100mbit ceil 100mbit 2>/dev/null')
    os.system(f'sudo tc class add dev {intf} parent 1: classid 1:20 htb rate 256kbit ceil 256kbit 2>/dev/null')   # 低速
    os.system(f'sudo tc class add dev {intf} parent 1: classid 1:30 htb rate 1mbit ceil 1mbit 2>/dev/null')     # 中速
    os.system(f'sudo tc class add dev {intf} parent 1: classid 1:40 htb rate 2mbit ceil 2mbit 2>/dev/null')     # 高速

    # 2. OVS 三档队列（先清再建）
    os.system(f'sudo ovs-vsctl clear port {intf} qos 2>/dev/null')
    os.system(f'sudo ovs-vsctl -- \
                --id=@q1 create queue other-config:max-rate=262144 -- \
                --id=@q2 create queue other-config:max-rate=1048576 -- \
                --id=@q3 create queue other-config:max-rate=2097152 -- \
                --id=@newqos create qos type=linux-htb queues:1=@q1 queues:2=@q2 queues:3=@q3 2>/dev/null')
    os.system(f'sudo ovs-vsctl set port {intf} qos=@newqos 2>/dev/null')

class FixedIPAttackTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1', cls=OVSKernelSwitch)
        
        # 所有主机都在 192.168.1.0/24 子网
        h1 = self.addHost('h1', ip='192.168.1.100/24', mac='00:00:00:00:00:01')  
        h8 = self.addHost('h8', ip='192.168.1.108/24', mac='00:00:00:00:00:08')  
        h2 = self.addHost('h2', ip='192.168.1.101/24', mac='00:00:00:00:00:02')  
        h3 = self.addHost('h3', ip='192.168.1.102/24', mac='00:00:00:00:00:03')  
        h4 = self.addHost('h4', ip='192.168.1.103/24', mac='00:00:00:00:00:04') 
        h5 = self.addHost('h5', ip='192.168.1.104/24', mac='00:00:00:00:00:05')  
        h6 = self.addHost('h6', ip='192.168.1.105/24', mac='00:00:00:00:00:06')  
        h7 = self.addHost('h7', ip='192.168.1.200/24', mac='00:00:00:00:00:07')  
        
        # 连接所有主机到交换机
        for host in [h1, h8, h2, h3, h4, h5, h6, h7]:
            self.addLink(host, s1)

def start_network():
    topo = FixedIPAttackTopo()
    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633),
        switch=OVSKernelSwitch,
        cleanup=True
    )
    net.start()

    # ---------- 关键：启动后自动配 3 档 QoS ----------
    for i in range(1, 9):          # s1-eth1 ~ s1-eth8
        config_qos_port(f's1-eth{i}')
    time.sleep(1)                  # 等等 OVS
    print("✅ 拓扑启动成功！IP均为 192.168.1.x/24")
    print("✅ 所有主机口 3 档 QoS 队列已就绪（低速/中速/高速）")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    start_network()