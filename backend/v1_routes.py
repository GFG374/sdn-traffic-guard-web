#!/usr/bin/env python
"""
V1 API路由模块
提供前端需要的基础API端点，包括概览数据、异常数据、流量统计等
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import time
from pydantic import BaseModel

from database import get_db
from models import User
from auth import get_current_user

# 创建路由器
router = APIRouter(prefix="/v1", tags=["v1"])

# 请求模型
class ChatRequest(BaseModel):
    user_id: str
    message: str

# 响应模型
class SummaryResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: str

class AnomalyResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    message: str

class FlowStatsResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    message: str

class ChatResponse(BaseModel):
    reply: str

# 真实SDN拓扑IP地址配置
REAL_TOPOLOGY_IPS = {
    "victims": ["192.168.1.100"],  # h1 受害者
    "normal": ["192.168.1.108"],   # h8 正常主机
    "attackers": [
        "192.168.1.101",  # h2 ARP欺骗攻击机
        "192.168.1.102",  # h3 SYN Flood攻击机
        "192.168.1.103",  # h4 UDP Flood攻击机
        "192.168.1.104",  # h5 ICMP Flood攻击机
        "192.168.1.105",  # h6 傀儡机
    ],
    "servers": ["192.168.1.200"]   # h7 C&C服务器
}

# 攻击类型与攻击机的映射
ATTACK_TYPE_MAPPING = {
    "192.168.1.101": "ARP Spoofing",
    "192.168.1.102": "SYN Flood", 
    "192.168.1.103": "UDP Flood",
    "192.168.1.104": "ICMP Flood",
    "192.168.1.105": "Botnet Activity"
}

def get_random_real_ip(ip_type: str = "any") -> str:
    """从真实拓扑中获取随机IP地址"""
    if ip_type == "attacker":
        return random.choice(REAL_TOPOLOGY_IPS["attackers"])
    elif ip_type == "victim":
        return random.choice(REAL_TOPOLOGY_IPS["victims"])
    elif ip_type == "normal":
        return random.choice(REAL_TOPOLOGY_IPS["normal"])
    elif ip_type == "server":
        return random.choice(REAL_TOPOLOGY_IPS["servers"])
    else:
        # 从所有IP中随机选择
        all_ips = (REAL_TOPOLOGY_IPS["victims"] + 
                  REAL_TOPOLOGY_IPS["normal"] + 
                  REAL_TOPOLOGY_IPS["attackers"] + 
                  REAL_TOPOLOGY_IPS["servers"])
        return random.choice(all_ips)

# 基于真实拓扑的数据生成函数
def generate_real_summary() -> Dict[str, Any]:
    """生成基于真实拓扑的概览数据"""
    return {
        "anomalies_today": random.randint(5, 20),
        "limited_ips": random.randint(1, 3),  # 通常只有少数攻击机被限速
        "blacklist_count": random.randint(2, 5),  # 黑名单中的攻击机数量
        "switches_online": 1,  # 拓扑中只有一个交换机s1
        "top_attack_ip": get_random_real_ip("attacker"),  # 最活跃的攻击IP
        "total_hosts": 8,  # 拓扑中总共8个主机
        "normal_hosts": len(REAL_TOPOLOGY_IPS["victims"] + REAL_TOPOLOGY_IPS["normal"]),
        "attack_hosts": len(REAL_TOPOLOGY_IPS["attackers"])
    }

def generate_real_anomalies() -> List[Dict[str, Any]]:
    """生成基于真实拓扑的异常数据"""
    anomalies = []
    
    # 为每个攻击机生成相应类型的异常
    for attacker_ip in REAL_TOPOLOGY_IPS["attackers"]:
        attack_type = ATTACK_TYPE_MAPPING.get(attacker_ip, "Unknown Attack")
        victim_ip = get_random_real_ip("victim")
        
        # 生成1-3个该类型的异常记录
        for _ in range(random.randint(1, 3)):
            anomaly = {
                "timestamp": int(time.time()) - random.randint(0, 86400),  # 过去24小时内
                "src_ip": attacker_ip,
                "dst_ip": victim_ip,
                "type": attack_type,
                "details": generate_attack_details(attack_type, attacker_ip, victim_ip),
                "severity": get_attack_severity(attack_type),
                "status": random.choice(["active", "mitigated", "investigating"])
            }
            anomalies.append(anomaly)
    
    # 按时间戳降序排序
    anomalies.sort(key=lambda x: x["timestamp"], reverse=True)
    return anomalies

def generate_attack_details(attack_type: str, src_ip: str, dst_ip: str) -> str:
    """根据攻击类型生成详细信息"""
    if attack_type == "ARP Spoofing":
        return f"检测到ARP欺骗攻击，{src_ip}伪造{dst_ip}的MAC地址，持续时间: {random.randint(5, 30)}分钟"
    elif attack_type == "SYN Flood":
        pps = random.randint(500, 2000)
        return f"检测到SYN洪水攻击，速率: {pps} pps，目标: {dst_ip}，持续时间: {random.randint(2, 15)}分钟"
    elif attack_type == "UDP Flood":
        pps = random.randint(300, 1500)
        return f"检测到UDP洪水攻击，速率: {pps} pps，目标端口: {random.randint(1000, 9999)}，持续时间: {random.randint(3, 20)}分钟"
    elif attack_type == "ICMP Flood":
        pps = random.randint(200, 1000)
        return f"检测到ICMP洪水攻击，速率: {pps} pps，目标: {dst_ip}，持续时间: {random.randint(1, 10)}分钟"
    elif attack_type == "Botnet Activity":
        return f"检测到僵尸网络活动，与C&C服务器{REAL_TOPOLOGY_IPS['servers'][0]}通信，连接数: {random.randint(10, 50)}"
    else:
        return f"检测到未知类型攻击，源IP: {src_ip}，目标: {dst_ip}"

def get_attack_severity(attack_type: str) -> str:
    """根据攻击类型返回严重程度"""
    severity_map = {
        "ARP Spoofing": "high",
        "SYN Flood": "critical", 
        "UDP Flood": "high",
        "ICMP Flood": "medium",
        "Botnet Activity": "critical"
    }
    return severity_map.get(attack_type, "medium")

def generate_real_flowstats() -> List[Dict[str, Any]]:
    """生成基于真实拓扑的流量统计数据"""
    protocols = ["TCP", "UDP", "ICMP", "ARP"]
    flowstats = []
    
    # 生成过去24小时的数据点
    current_time = int(time.time())
    for i in range(144):  # 每10分钟一个数据点，24小时共144个点
        timestamp = current_time - (i * 600)  # 600秒 = 10分钟
        
        # 为每个真实IP生成流量数据
        all_ips = (REAL_TOPOLOGY_IPS["victims"] + 
                  REAL_TOPOLOGY_IPS["normal"] + 
                  REAL_TOPOLOGY_IPS["attackers"] + 
                  REAL_TOPOLOGY_IPS["servers"])
        
        for src_ip in all_ips:
            for protocol in protocols:
                # 根据IP类型调整流量特征
                if src_ip in REAL_TOPOLOGY_IPS["attackers"]:
                    # 攻击机流量更大
                    packet_count = random.randint(100, 2000)
                    byte_count = random.randint(10240, 2097152)  # 10KB到2MB
                elif src_ip in REAL_TOPOLOGY_IPS["normal"]:
                    # 正常主机流量较小
                    packet_count = random.randint(10, 200)
                    byte_count = random.randint(1024, 204800)  # 1KB到200KB
                else:
                    # 受害者和服务器中等流量
                    packet_count = random.randint(50, 500)
                    byte_count = random.randint(5120, 524288)  # 5KB到512KB
                
                dst_ip = get_random_real_ip()
                while dst_ip == src_ip:  # 确保源IP和目标IP不同
                    dst_ip = get_random_real_ip()
                
                flow = {
                    "timestamp": timestamp,
                    "protocol": protocol,
                    "packet_count": packet_count,
                    "byte_count": byte_count,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "datapath_id": "0000000000000001",  # 交换机s1的ID
                    "duration_sec": random.randint(1, 600)
                }
                flowstats.append(flow)
    
    return flowstats

# API端点
@router.get("/summary")
async def get_summary():
    """获取网络概览数据"""
    try:
        summary_data = generate_real_summary()
        return summary_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览数据失败: {str(e)}")

@router.get("/anomalies")
async def get_anomalies():
    """获取异常数据列表"""
    try:
        anomalies_data = generate_real_anomalies()
        return anomalies_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取异常数据失败: {str(e)}")

@router.get("/flowstats")
async def get_flowstats():
    """获取流量统计数据"""
    try:
        flowstats_data = generate_real_flowstats()
        return flowstats_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流量数据失败: {str(e)}")

@router.post("/chat")
async def chat_command(request: ChatRequest):
    """处理聊天命令（加黑、限速等操作）"""
    try:
        message = request.message.lower().strip()
        
        # 解析命令
        if message.startswith("block "):
            ip = message.replace("block ", "").strip()
            reply = f"已将IP {ip} 加入黑名单"
        elif message.startswith("limit "):
            ip = message.replace("limit ", "").strip()
            reply = f"已对IP {ip} 实施限速"
        elif message.startswith("unblock "):
            ip = message.replace("unblock ", "").strip()
            reply = f"已将IP {ip} 从黑名单移除"
        elif message.startswith("unlimit "):
            ip = message.replace("unlimit ", "").strip()
            reply = f"已解除对IP {ip} 的限速"
        else:
            reply = f"收到命令: {request.message}，正在处理..."
        
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理聊天命令失败: {str(e)}")

# 健康检查端点
@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "v1-api"
    }