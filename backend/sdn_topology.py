#!/usr/bin/env python

"""
SDN网络拓扑配置文件
此脚本使用Mininet和RYU控制器创建一个基础的SDN网络拓扑
"""

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink


def create_topology():
    """创建SDN网络拓扑"""
    # 创建网络，指定使用Open vSwitch交换机和远程RYU控制器
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink
    )
    
    # 添加RYU控制器，默认监听127.0.0.1:6633
    c0 = net.addController('c0', ip='127.0.0.1', port=6633)
    
    # 添加交换机，明确指定DPID
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')
    s3 = net.addSwitch('s3', dpid='0000000000000003')
    s4 = net.addSwitch('s4', dpid='0000000000000004')
    
    # 添加主机
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')
    
    # 创建链路，设置带宽和延迟
    # 交换机互联
    net.addLink(s1, s2, bw=1000, delay='1ms')  # 1Gbps链路，1ms延迟
    net.addLink(s2, s3, bw=1000, delay='1ms')
    net.addLink(s3, s4, bw=1000, delay='1ms')
    net.addLink(s4, s1, bw=1000, delay='1ms')
    
    # 主机连接到交换机
    net.addLink(h1, s1, bw=100, delay='5ms')  # 100Mbps链路，5ms延迟
    net.addLink(h2, s2, bw=100, delay='5ms')
    net.addLink(h3, s3, bw=100, delay='5ms')
    net.addLink(h4, s4, bw=100, delay='5ms')
    
    # 启动网络
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])
    s4.start([c0])
    
    print("\nSDN网络拓扑创建完成!")
    print("控制器: RYU (运行在 127.0.0.1:6633)")
    print("交换机: s1, s2, s3, s4")
    print("主机: h1(10.0.0.1), h2(10.0.0.2), h3(10.0.0.3), h4(10.0.0.4)")
    print("\n输入'help'查看可用命令，输入'quit'退出")
    
    # 启动CLI交互界面
    CLI(net)
    
    # 停止网络
    net.stop()


def create_tree_topology(depth=2, fanout=2):
    """创建树形拓扑
    参数:
        depth: 树的深度
        fanout: 每个交换机的子节点数量
    """
    from mininet.topolib import TreeTopo
    
    # 创建树形拓扑
    topo = TreeTopo(depth=depth, fanout=fanout)
    
    # 创建网络
    net = Mininet(
        topo=topo,
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink
    )
    
    # 添加控制器
    c0 = net.addController('c0', ip='127.0.0.1', port=6633)
    
    # 启动网络
    net.build()
    c0.start()
    for switch in net.switches:
        switch.start([c0])
    
    print(f"\n树形SDN网络拓扑创建完成! (深度: {depth}, 扇出: {fanout})")
    print("控制器: RYU (运行在 127.0.0.1:6633)")
    print("交换机数量: {}".format(len(net.switches)))
    print("主机数量: {}".format(len(net.hosts)))
    print("\n输入'help'查看可用命令，输入'quit'退出")
    
    # 启动CLI交互界面
    CLI(net)
    
    # 停止网络
    net.stop()


def create_ryu_app():
    """创建一个简单的RYU应用示例文件"""
    app_content = '''#!/usr/bin/env python

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly. The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
'''
    
    with open('simple_switch_13.py', 'w') as f:
        f.write(app_content)
    
    print("\n已创建RYU应用示例文件: simple_switch_13.py")


def create_topology_config_file():
    """创建拓扑配置说明文件"""
    config_content = '''# SDN拓扑配置说明

## 环境要求
- Mininet
- Ryu控制器
- Open vSwitch

## 安装依赖
```bash
# 安装Mininet
sudo apt-get install mininet

# 安装RYU控制器
pip install ryu

# 安装Open vSwitch
sudo apt-get install openvswitch-switch
```

## 使用方法

### 1. 启动RYU控制器
```bash
# 使用示例应用启动RYU控制器
ryu-manager simple_switch_13.py
```

### 2. 运行拓扑脚本
```bash
# 运行默认拓扑
python sdn_topology.py

# 或运行树形拓扑
python -c "from sdn_topology import create_tree_topology; create_tree_topology(depth=2, fanout=3)"
```

### 3. Mininet CLI常用命令
- `nodes`: 查看所有节点
- `net`: 查看网络拓扑
- `links`: 查看所有链路
- `pingall`: 所有主机互相ping
- `h1 ping h2`: 特定主机之间ping
- `dpctl dump-flows`: 查看交换机流表
- `exit` 或 `quit`: 退出CLI

## 自定义拓扑
修改`sdn_topology.py`文件中的`create_topology()`函数，可以自定义:
- 交换机数量和连接方式
- 主机数量和IP配置
- 链路带宽和延迟参数

## 控制器配置
- 默认控制器地址: 127.0.0.1:6633
- 可在`create_topology()`函数中修改控制器IP和端口

## 高级功能
- 可以扩展RYU应用实现更复杂的网络功能
- 支持流表操作、QoS配置、安全策略等
'''
    
    with open('SDN_TOPOLOGY_GUIDE.md', 'w') as f:
        f.write(config_content)
    
    print("\n已创建拓扑配置说明文件: SDN_TOPOLOGY_GUIDE.md")


if __name__ == '__main__':
    # 设置日志级别
    setLogLevel('info')
    
    print("""
    ======================================
           SDN网络拓扑配置工具
    ======================================
    选项:
    1. 创建默认拓扑 (4交换机4主机的环形拓扑)
    2. 创建树形拓扑
    3. 生成RYU应用示例
    4. 生成拓扑配置说明
    """)
    
    choice = input("请选择操作 (1-4): ")
    
    if choice == '1':
        create_topology()
    elif choice == '2':
        try:
            depth = int(input("请输入树的深度: "))
            fanout = int(input("请输入扇出数: "))
            create_tree_topology(depth=depth, fanout=fanout)
        except ValueError:
            print("输入无效，使用默认值 (深度=2, 扇出=2)")
            create_tree_topology()
    elif choice == '3':
        create_ryu_app()
    elif choice == '4':
        create_topology_config_file()
    else:
        print("无效选择，退出程序")